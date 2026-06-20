from langchain_tavily import TavilySearch

search_tool = TavilySearch(
    max_results=5,
    search_depth="advanced", #basic or advanced
    include_raw_content=False,
    include_images=False
)

