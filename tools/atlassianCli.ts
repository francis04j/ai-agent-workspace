// Shared Atlassian CLI (acli) error detection, classification, and remedy messaging.
// Used by Jira helper tools and any code that shells out to `acli`.

import { spawnSync } from 'child_process';
import { writeFileSync, unlinkSync, mkdirSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';

// ToolResponse type for Jira tool integration.
export interface ToolResponse<TData = unknown> {
    status: 'success' | 'fail' | 'fix';
    message: string;
    data?: TData;
}

export type AcliErrorClass =
    | 'not-installed'
    | 'auth'
    | 'ssl'
    | 'proxy'
    | 'connection'
    | 'not-found'
    | 'permission'
    | 'rate-limit'
    | 'invalid-request'
    | 'unknown';

const ACLI_SETUP_GUIDE = 'See: tools/README.md';

export const ACLI_LOGIN_REMEDY =
    'Run: acli jira auth login --web\n' +
    'Or set environment variables:\n' +
    '  ATLASSIAN_EMAIL=your.email@company.com\n' +
    '  ATLASSIAN_API_TOKEN=your-api-token\n' +
    `${ACLI_SETUP_GUIDE}`;

const ACLI_DIAGNOSTIC_COMMANDS_UNIX =
    'Diagnostic commands (macOS/Linux):\n' +
    '  acli jira auth status           # check auth status\n' +
    '  env | grep -i proxy             # check proxy settings\n' +
    '  curl -v https://your-domain.atlassian.net  # test connectivity';

const ACLI_DIAGNOSTIC_COMMANDS_WINDOWS =
    'Diagnostic commands (Windows PowerShell):\n' +
    '  acli jira auth status           # check auth status\n' +
    '  $env:HTTPS_PROXY                # check proxy settings\n' +
    '  Invoke-WebRequest -Uri "https://your-domain.atlassian.net" -Method Head  # test connectivity';

function getDiagnosticCommands(): string {
    return process.platform === 'win32'
        ? ACLI_DIAGNOSTIC_COMMANDS_WINDOWS
        : ACLI_DIAGNOSTIC_COMMANDS_UNIX;
}

export function classifyAcliError(text: string): AcliErrorClass {
    const lowerText = text.toLowerCase();

    if (
        /unauthorized|401|authentication failed|invalid credentials|api token/i.test(text) ||
        /not logged in|please log in|login required/i.test(text)
    ) {
        return 'auth';
    }

    if (/SSLError|SSL:\s*CERTIFICATE_VERIFY_FAILED|certificate verify failed|CERT_/i.test(text)) {
        return 'ssl';
    }

    if (/ProxyError|Unable to connect to proxy|proxy authentication/i.test(text)) {
        return 'proxy';
    }

    if (
        /NewConnectionError|Max retries exceeded|ConnectionError|Failed to establish connection/i.test(text) ||
        /ECONNREFUSED|ETIMEDOUT|ENOTFOUND|getaddrinfo|network is unreachable/i.test(text)
    ) {
        return 'connection';
    }

    if (
        /404|not found|does not exist|no such issue|issue .* not found/i.test(text) ||
        /project .* not found|board .* not found/i.test(text)
    ) {
        return 'not-found';
    }

    if (/403|forbidden|permission denied|access denied|you do not have permission/i.test(text)) {
        return 'permission';
    }

    if (/429|rate limit|too many requests|throttl/i.test(text)) {
        return 'rate-limit';
    }

    if (/400|bad request|invalid request|validation failed|invalid field/i.test(text)) {
        return 'invalid-request';
    }

    if (
        /command not found|not recognized|cannot find|ENOENT.*acli/i.test(text) ||
        /'acli' is not recognized/i.test(text)
    ) {
        return 'not-installed';
    }

    void lowerText;
    return 'unknown';
}

export function isNetworkError(errorClass: AcliErrorClass): boolean {
    return errorClass === 'ssl' || errorClass === 'proxy' || errorClass === 'connection';
}

export function buildFixMessage(errorClass: AcliErrorClass, rawDetail: string): string {
    const remedies: string[] = [];

    switch (errorClass) {
        case 'not-installed':
            remedies.push(
                'Atlassian CLI (acli) not found.',
                'Install from: https://developer.atlassian.com/cloud/acli/guides/introduction/',
                'Windows install guide: https://developer.atlassian.com/cloud/acli/guides/install-windows/',
                'Download releases: https://packages.atlassian.com/acli/latest/',
                'For jira-read-work-item: abort workflow and run setup first.',
                ACLI_SETUP_GUIDE,
            );
            break;

        case 'auth':
            remedies.push(`Authentication failed. ${ACLI_LOGIN_REMEDY}`);
            break;

        case 'ssl':
            remedies.push(
                'SSL certificate verification failed. Likely causes:',
                '1. Missing CA bundle: export REQUESTS_CA_BUNDLE=/path/to/ca-bundle.pem',
                '2. Corporate proxy/Zscaler: the proxy\'s root CA must be in your CA bundle',
                '3. VPN/Zscaler toggle: reconnecting may require updating proxy env vars',
            );
            break;

        case 'proxy':
            remedies.push(
                'Proxy connection failed. Likely causes:',
                '1. HTTPS_PROXY is set but proxy is unreachable (VPN disconnected, wrong port)',
                '2. no_proxy may need updating: add your-domain.atlassian.net if direct access works',
                '3. Stale proxy settings from a previous VPN/Zscaler session',
            );
            break;

        case 'connection':
            remedies.push(
                'Network connection failed. Likely causes:',
                '1. No network connectivity to Atlassian (your-domain.atlassian.net)',
                '2. Proxy misconfiguration: check HTTPS_PROXY and no_proxy env vars',
                '3. DNS resolution failure: verify your Jira domain resolves',
                '4. Firewall blocking outbound HTTPS (port 443)',
            );
            break;

        case 'not-found':
            remedies.push(
                'Resource not found. Verify:',
                '1. The issue/project key is correct (e.g., PROJ-123)',
                '2. You have access to the project in Jira',
                '3. The issue hasn\'t been deleted or moved',
            );
            break;

        case 'permission':
            remedies.push(
                'Permission denied. Verify:',
                '1. Your Jira account has access to this project',
                '2. The API token has sufficient permissions',
                '3. Project permissions haven\'t changed recently',
            );
            break;

        case 'rate-limit':
            remedies.push(
                'Rate limit exceeded. Options:',
                '1. Wait a few minutes and retry',
                '2. Reduce request frequency',
                '3. Check Atlassian rate limit headers for reset time',
            );
            break;

        case 'invalid-request':
            remedies.push(
                'Invalid request (400 Bad Request). Likely causes:',
                '1. Invalid field name or value in the request',
                '2. Unsupported parameter (e.g., obsolete currency code, invalid date)',
                '3. Malformed query syntax',
            );
            break;

        case 'unknown':
            break;
    }

    if (isNetworkError(errorClass)) {
        remedies.push(getDiagnosticCommands());
    }

    const detail = rawDetail.slice(0, 400);
    return remedies.length > 0
        ? `${remedies.join('\n')}\n\nRaw error: ${detail}`
        : `Atlassian CLI error: ${detail}`;
}

export type AcliResult =
    | { success: true; stdout: string }
    | { success: false; stderr: string; errorClass: AcliErrorClass; message: string };

export interface ExecuteAcliOptions {
    cwd?: string;
    timeout?: number;
}

function getAcliCommand(): string {
    return process.env.ACLI_PATH || 'acli';
}

export function executeAcli(args: string[], options: ExecuteAcliOptions = {}): AcliResult {
    const { cwd, timeout = 60000 } = options;
    const acliCmd = getAcliCommand();

    try {
        const envWithNoPager = {
            ...process.env,
            PAGER: 'cat',
            GIT_PAGER: 'cat',
            LESS: 'FRX',
        };

        const result = spawnSync(acliCmd, args, {
            cwd,
            encoding: 'utf-8',
            timeout,
            env: envWithNoPager,
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: process.platform === 'win32',
        });

        if (result.error) {
            const stderr = result.stderr || result.error.message;
            const errorClass = classifyAcliError(stderr);
            return {
                success: false,
                stderr,
                errorClass,
                message: buildFixMessage(errorClass, stderr),
            };
        }

        if (result.status !== 0) {
            const stderr = result.stderr || '';
            const errorClass = classifyAcliError(stderr);
            const fallback = stderr.split('\n')[0] || `exit code ${result.status}`;
            return {
                success: false,
                stderr,
                errorClass,
                message: errorClass !== 'unknown'
                    ? buildFixMessage(errorClass, stderr)
                    : `Atlassian CLI error: ${fallback}`,
            };
        }

        return { success: true, stdout: result.stdout.trim() };
    } catch (error) {
        const stderr = error instanceof Error ? error.message : String(error);
        const errorClass = classifyAcliError(stderr);
        return {
            success: false,
            stderr,
            errorClass,
            message: buildFixMessage(errorClass, stderr),
        };
    }
}

export function executeAcliWithPayload(
    args: string[],
    payload: string,
    options: ExecuteAcliOptions = {},
): AcliResult {
    const tmpFile = join(tmpdir(), `jira-acli-payload-${Date.now()}.json`).replace(/\\/g, '/');
    try {
        writeFileSync(tmpFile, payload, 'utf-8');
        const modifiedArgs = args.map((arg) => (arg === '-' ? tmpFile : arg));
        const result = executeAcli(modifiedArgs, options);
        try { unlinkSync(tmpFile); } catch { }
        return result;
    } catch (error) {
        try { unlinkSync(tmpFile); } catch { }
        const stderr = error instanceof Error ? error.message : String(error);
        return {
            success: false,
            stderr,
            errorClass: 'unknown',
            message: `Atlassian CLI error: ${stderr.slice(0, 300)}`,
        };
    }
}

export function hasAcli(): boolean {
    const acliCmd = getAcliCommand();
    try {
        const result = spawnSync(acliCmd, ['--version'], {
            encoding: 'utf8',
            stdio: ['pipe', 'pipe', 'pipe'],
            timeout: 5000,
            shell: process.platform === 'win32',
        });
        return result.status === 0 && !result.error;
    } catch {
        return false;
    }
}

export function checkAcliAuth(): AcliResult {
    return executeAcli(['jira', 'auth', 'status']);
}

export function isAuthenticated(): boolean {
    const result = checkAcliAuth();
    if (!result.success) return false;
    return /authenticated|logged in|✓/i.test(result.stdout);
}

export interface JiraTicketOptions {
    fields?: string;
    outputDir?: string;
}

export function fetchJiraTicket(ticketKey: string, options: JiraTicketOptions = {}): AcliResult {
    const { fields = '*all' } = options;
    const args = ['jira', 'workitem', 'view', ticketKey, '--fields', fields, '--json'];
    return executeAcli(args);
}

export function ensureOutputDir(dirPath: string): void {
    mkdirSync(dirPath, { recursive: true });
}

export function saveTicketJson(ticketKey: string, jsonContent: string, outputDir: string): string {
    ensureOutputDir(outputDir);
    const filePath = join(outputDir, `${ticketKey}-raw.json`);
    writeFileSync(filePath, jsonContent, 'utf-8');
    return filePath;
}

export function buildNoCliResponse(): ToolResponse {
    return {
        status: 'fail',
        message:
            'Atlassian CLI (acli) not found. ' +
            'For jira-read-work-item, abort and complete setup first.\n' +
            `${ACLI_SETUP_GUIDE}\n` +
            'After setup, retry: npx jira-read-work-item --key <ISSUE-KEY>\n' +
            `Then authenticate: ${ACLI_LOGIN_REMEDY}`,
    };
}

export function extractStderr(error: Error): string {
    const cause = error.cause;
    if (cause && typeof cause === 'object' && 'stderr' in cause) {
        return String((cause as { stderr: unknown }).stderr);
    }
    return '';
}

export function fetchAndSaveTicket(
    ticketKey: string,
    outputDir: string,
): AcliResult & { filePath?: string } {
    if (!hasAcli()) {
        return {
            success: false,
            stderr: 'acli not found',
            errorClass: 'not-installed',
            message: buildNoCliResponse().message,
        };
    }

    if (!isAuthenticated()) {
        return {
            success: false,
            stderr: 'Not authenticated',
            errorClass: 'auth',
            message: buildFixMessage('auth', 'Not authenticated to Jira'),
        };
    }

    const ticketResult = fetchJiraTicket(ticketKey);
    if (!ticketResult.success) {
        return ticketResult;
    }

    const filePath = saveTicketJson(ticketKey, ticketResult.stdout, outputDir);
    return { ...ticketResult, filePath };
}
