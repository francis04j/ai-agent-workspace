# Simple Agent Console

Run the movie agent app from this folder.

## 1. Create and activate a virtual environment

```bash
cd /Users/francisadediran/development/ai-agent-workspace/simple-agent-console
python3 -m venv .venv
source .venv/bin/activate
```

## 2. Install dependencies (pyproject)

```bash
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .
```

If editable install fails, install dependencies directly:

```bash
python -m pip install langchain-core langchain-anthropic langgraph python-dotenv pydantic
```

## 3. Configure environment variables

```bash
cp .env.example .env
```

Add your Anthropic key to `.env`:

```dotenv
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

## 4. Run the app

```bash
simple-agent-console

# alternative
python -m main
```

## 5. Quick checks

```bash
python -m py_compile src/main.py
python -c "from create_agent import create_agent; print('create_agent import ok')"
```
