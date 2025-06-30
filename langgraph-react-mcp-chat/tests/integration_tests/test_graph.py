import pytest
from langsmith import unit

from react_agent import graph


@pytest.mark.asyncio
@unit
async def test_react_agent_simple_passthrough() -> None:
    res = await graph.ainvoke(
        {"messages": [("user", "Hi, Tell me your abilities")]},
        {"configurable": {"system_prompt": "You are a helpful AI assistant."}},
    )

    assert "harrison" in str(res["messages"][-1].content).lower()
