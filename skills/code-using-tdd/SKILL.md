---
name: code-using-tdd
description: Implement code changes using rigorous test-driven development practices following red-green-refactor cycles with comprehensive test coverage validation. Ideal for implementation-focused requests in projects with existing test frameworks.
---

# Code Using TDD

## Purpose

Implement code changes using strict test-driven development methodology following red-green-refactor cycles.

## How It Works

This skill guides an AI agent through a tight TDD loop:

1. Identify one small, testable behavior.
2. Write or update a failing test for that behavior.
3. Implement the minimum code needed to make the test pass.
4. Refactor without breaking the tests.
5. Repeat the cycle for the next behavior until the change is complete.

The skill is most useful when the request is implementation-focused and the project already has a working test framework.

**Key Characteristics:**

- Write failing tests first, then implement
- Minimal code to pass tests
- Refactor while maintaining coverage

**When to use:**

- User explicitly requests TDD
- Dynamically typed languages such as Python or JavaScript where missing types do not block test compilation
- Strongly typed languages where types and contracts already exist
- Planned implementation tasks that can be broken into small, testable units

**When to avoid:**

- Strongly typed languages where key types and interfaces do not exist yet
- Discovery or orchestration work
- Non-code tasks

## Example Prompts

Use prompts like these in Copilot Chat:

```text
Use the code-using-tdd skill to implement this bug fix.
```

```text
Apply code-using-tdd for this feature and show each red-green-refactor cycle.
```

```text
Implement the next task with code-using-tdd. Start by writing the failing test.
```

```text
Use code-using-tdd for this Python change. Break the work into small testable units and complete them one by one.
```

## Step 1: Understand Requirements

Review requirements from the issue, work item, plan, or user request. Identify testable behaviors, edge cases, and error conditions. Break down functionality into a numbered list of testable units.

---

**TDD CYCLE START - Repeat Steps 2-4 for EACH testable unit**

## Step 2: Write Failing Tests (Red Phase)

For each testable unit, write tests before implementation:

**Test Structure:**

- Descriptive names following the project's existing test naming convention
- AAA pattern: Arrange, Act, Assert
- One behavior per test
- Cover happy path, edge cases, and error conditions

**Test Implementation:**

- Use the project's existing test framework
- Use the project's standard assertion style for readable failures
- Mock dependencies with the project's preferred mocking utilities when needed
- Run tests to confirm they fail with clear messages

---

## Step 3: Implement Minimal Code (Green Phase)

Write the simplest code that makes the tests pass:

- Implement only what tests require
- Avoid over-engineering
- Follow existing code patterns
- Verify all tests pass
- Run the relevant test suite for the current unit

---

## Step 4: Refactor

Improve code while maintaining test coverage:

- Enhance clarity and design
- Remove duplication
- Follow SOLID principles and clean code practices
- Ensure all tests still pass after refactoring

**After refactor, present:**

```
TDD Cycle [N] of [M] complete: [what was tested]
- Tests written: [count]
- Tests passing: [count]
- Next unit: [description]

[CONTINUE or REVIEW before next cycle]
```

**If blocked** (test will not compile, requirement is unclear, dependency is missing):

- STOP -- do not continue to the next cycle
- Report what failed, what is needed, and the available options
- Wait for human decision before resuming

**If units remain:** Return to Step 2 for the next testable unit
**If all units complete:** Proceed to Quality Checklist

**TDD CYCLE END**

---

## Quality Checklist

Before considering implementation complete, verify:

- [ ] All critical paths tested
- [ ] Edge cases and error conditions covered
- [ ] Tests can run in any order with no shared state dependencies
- [ ] Tests are deterministic and repeatable
- [ ] Test names clearly describe behavior
- [ ] No complex test logic or setup
- [ ] All tests pass consistently

---

## Notes

- Focus on one behavior at a time -- complete the full red-green-refactor cycle before starting the next
- Write minimal code to pass tests -- no functionality beyond test requirements
- Run tests frequently and fix failures immediately
- Test failures should have meaningful error messages
