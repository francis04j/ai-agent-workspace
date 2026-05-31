from langgraph.prebuilt import create_react_agent as Agent

def create_agent(model, tools, verbose=False):
    """Create an agent from a model and tool list."""
    _ = verbose
    return Agent(model=model, tools=tools)

