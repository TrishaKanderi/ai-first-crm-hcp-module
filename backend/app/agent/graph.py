"""
The LangGraph agent that powers the conversational side of the Log Interaction
Screen.

Role of the agent: it sits between the free-text chat box a field rep types
into and the structured CRM database. Its job is to (a) figure out which sales
activity the rep is describing or asking for, (b) call the right tool to read
or write that data, and (c) turn the tool's structured result back into a short,
useful reply - so the rep never has to touch a form if they don't want to.

We use langgraph's prebuilt `create_react_agent`, which wires up a standard
ReAct-style graph for us: an LLM node bound to our 5 tools, a conditional edge
that routes to a tool node whenever the LLM emits a tool call, and a loop back
to the LLM node until it produces a final answer. This is enough control for
this task - the five tools are largely independent actions rather than a
multi-stage pipeline that would need a hand-rolled graph.
"""
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from app.agent.llm import get_default_llm
from app.agent.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the AI assistant embedded in a pharma field rep's CRM,
on the "Log Interaction" screen for Healthcare Professional (HCP) visits.

You have 5 tools: log_interaction, edit_interaction, get_interaction_history,
schedule_follow_up, and flag_compliance_risk.

Guidelines:
- If the rep describes a visit/call that sounds new, call log_interaction.
- After logging a new interaction, also call flag_compliance_risk on it so risky
  content (adverse events, off-label claims) is never silently missed.
- If the rep refers to something already logged and wants to change it, call
  edit_interaction (they'll usually give or you'll infer the interaction_id from
  recent conversation).
- If they ask what happened last time with an HCP, call get_interaction_history.
- If they mention something they still need to do, call schedule_follow_up.
- Keep replies short, concrete, and specific to what changed - like a helpful
  coworker confirming an action, not a chatbot narrating its own reasoning.
"""

_checkpointer = MemorySaver()

_agent = create_react_agent(
    model=get_default_llm(),
    tools=ALL_TOOLS,
    state_modifier=SYSTEM_PROMPT,
    checkpointer=_checkpointer,
)


def run_agent(message: str, thread_id: str = "default"):
    """Invoke the agent graph for one chat turn and return (reply_text, tool_calls)."""
    config = {"configurable": {"thread_id": thread_id}}
    result = _agent.invoke({"messages": [("user", message)]}, config=config)
    messages = result["messages"]

    final_text = messages[-1].content

    tool_calls = []
    for m in messages:
        if getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                tool_calls.append(tc["name"])
        if getattr(m, "name", None):  # ToolMessage carries the tool's own name
            tool_calls.append(m.name)

    return final_text, tool_calls
