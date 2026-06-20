import random

from langchain_core.tools import tool

# Mock datastore that simulates rows in a movies table.
_MOVIE_ROWS = [
    {
        "title": "Inception",
        "director": "Christopher Nolan",
        "year": 2010,
        "description": "A thief enters dreams to plant an idea.",
    },
    {
        "title": "Interstellar",
        "director": "Christopher Nolan",
        "year": 2014,
        "description": "A team travels through a wormhole to save humanity.",
    },
    {
        "title": "The Dark Knight",
        "director": "Christopher Nolan",
        "year": 2008,
        "description": "Batman faces Joker in Gotham City.",
    },
    {
        "title": "Pulp Fiction",
        "director": "Quentin Tarantino",
        "year": 1994,
        "description": "Interwoven crime stories in Los Angeles.",
    },
    {
        "title": "Dune",
        "director": "Denis Villeneuve",
        "year": 2021,
        "description": "A noble family fights for control of Arrakis.",
    },
]


@tool
def lookup_movie_tool(title: str) -> str:
    """Mock DB lookup for a movie title and return a random matching row."""
    normalized_title = title.strip().lower()
    matches = [row for row in _MOVIE_ROWS if normalized_title in row["title"].lower()]
    if not matches:
        # Simulate fallback query returning a random recommendation.
        random_row = random.choice(_MOVIE_ROWS)
        return (
            "No exact database match found. "
            f"Suggested record: {random_row['title']} ({random_row['year']}), "
            f"directed by {random_row['director']}."
        )

    row = random.choice(matches)
    return (
        f"{row['title']} ({row['year']}) directed by {row['director']}. "
        f"Description: {row['description']}"
    )


@tool
def lookup_movies_by_director_tool(director: str) -> str:
    """Mock DB lookup by director and return random matching results."""
    normalized_director = director.strip().lower()
    matches = [row for row in _MOVIE_ROWS if normalized_director in row["director"].lower()]
    if not matches:
        random_row = random.choice(_MOVIE_ROWS)
        return (
            "No director match found in mock database. "
            f"Random row: {random_row['title']} by {random_row['director']} "
            f"({random_row['year']})."
        )

    row = random.choice(matches)
    return (
        f"{row['title']} ({row['year']}) directed by {row['director']}. "
        f"Description: {row['description']}"
    )
