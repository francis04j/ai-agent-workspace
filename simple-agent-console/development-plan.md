# Development Plan: Run `python main.py` in `simple-agent-console`

Quick status: `main.py` currently has unresolved imports and undefined symbols, and `.env.example` is empty. This is why `python main.py` does not run yet.

## 1. Stabilize `main.py` first

- Replace non-existent imports in `main.py`:
  - remove `langchain_agent` and `langchain_tools` imports
  - use real modules (for example `langchain_core.tools` and `langgraph.prebuilt`), or simplify to a no-agent version
- Define every currently missing symbol:
  - `create_agent`
  - `lookup_movie_tool`
  - `lookup_movies_by_director`
- Add startup guards:
  - check `OPENAI_API_KEY`
  - print a clear error and exit if missing

## 2. Add dependency manifest in the same folder

- Create `requirements.txt` in `simple-agent-console` with exact runtime packages.
- Initial set (adjust after final code path):
  - `langchain-openai`
  - `langgraph`
  - `python-dotenv`
  - `pydantic`

## 3. Add environment template

- Populate `.env.example` with:
  - `OPENAI_API_KEY=your_key_here`
  - `OPENAI_MODEL=gpt-4.1-mini`
- Keep `.env` for your real secret locally.

## 4. Optional but recommended module split (cleaner and easier to debug)

- Generate `movie_tools.py`:
  - put `lookup_movie_tool` and `lookup_movies_by_director` here
- Keep `main.py` focused on:
  - loading env
  - model/agent creation
  - CLI entrypoint

This reduces import/undefined errors and keeps logic testable.

## 5. Add run instructions file

- Create `README.md` in `simple-agent-console` with:
  - `python -m venv .venv`
  - `source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - `cp .env.example .env`
  - `python main.py`

## 6. Validate end-to-end

- Run from inside `simple-agent-console`:
  - `python -m py_compile main.py`
  - `python main.py`
- If model/provider errors appear, refine env and dependency versions.

## Minimum files to generate

- `requirements.txt`
- `README.md`
- `movie_tools.py` (recommended)
- update `.env.example`
- update `main.py`
