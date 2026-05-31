import os
import sys
from pathlib import Path
from typing import Any

from create_agent import create_agent
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from typing import Optional
from tools import lookup_movie_tool, lookup_movies_by_director_tool

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def _require_api_keys() -> None:
    """Fail fast with a clear message if ANTHROPIC_API_KEY is missing."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Startup error: ANTHROPIC_API_KEY is missing. Set it in your environment or .env file.")
        sys.exit(1)


class Movie(BaseModel):
    "Model for extracting movie information from text"
    title: str = Field(..., description="The title of the movie")
    director: str = Field(..., description="The director of the movie")
    year: int = Field(..., description="The release year of the movie")
    description: Optional[str] = Field(default=None,
                                        description="A brief description of the movie")

tools = [lookup_movie_tool, lookup_movies_by_director_tool]


def _build_base_model() -> ChatAnthropic:
    return ChatAnthropic(
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        temperature=0.1,
    )


def build_structured_movie_model():
    return _build_base_model().with_structured_output(Movie)


def build_movie_agent():
    return create_agent(model=_build_base_model(), tools=tools)


def extract_movie(text: str) -> Movie:
    structured_model = build_structured_movie_model()
    return structured_model.invoke(text)


def ask_movie_agent(question: str) -> str:
    """Helper function to query the movie agent."""
    movie_agent = build_movie_agent()
    result = movie_agent.invoke({
        "messages": [{"role": "user", "content": question}]
    })

    final_message = result["messages"][-1]
    if hasattr(final_message, "content"):
        content: Any = final_message.content
    else:
        content = final_message["content"]

    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
            elif hasattr(part, "text"):
                text_parts.append(part.text)
            else:
                text_parts.append(str(part))
        return "\n".join(text_parts)
    return str(content)


def ask_movie_agent_structured(question: str) -> Movie:
    """Return a validated Movie object from the agent response."""
    raw_response = ask_movie_agent(question)

    extraction_prompt = (
        "Extract exactly one movie object from the text below. "
        "Return fields for title, director, year, and description.\n\n"
        f"Text:\n{raw_response}"
    )

    try:
        return extract_movie(extraction_prompt)
    except Exception:
        retry_prompt = (
            "Pick the first clearly named movie in the text and return one Movie object only. "
            "If multiple movies are listed, do not return an array.\n\n"
            f"Text:\n{raw_response}"
        )
        return extract_movie(retry_prompt)


def main() -> int:
    _require_api_keys()
    print("Asking: What movies did Christopher Nolan direct?")
    movie = ask_movie_agent_structured("What movies did Christopher Nolan direct?")
    print(movie.model_dump_json(indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
