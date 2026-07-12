"""
Thin wrapper around Groq-hosted LLMs via langchain-groq.

gemma2-9b-it is used as the default "workhorse" model for the agent's tool-routing
and everyday extraction/summarization calls because it's fast and cheap, which
matters for a field-rep-facing tool that needs snappy responses after every visit.

llama-3.3-70b-versatile is wired in as a fallback for the one step that benefits
most from stronger reasoning: compliance / adverse-event flagging, where a missed
detection has real regulatory consequences.
"""
from langchain_groq import ChatGroq
from app.config import GROQ_API_KEY, GROQ_MODEL, GROQ_MODEL_LARGE

_common_kwargs = dict(api_key=GROQ_API_KEY, temperature=0)

def get_default_llm():
    return ChatGroq(model=GROQ_MODEL, **_common_kwargs)


def get_large_llm():
    return ChatGroq(model=GROQ_MODEL_LARGE, **_common_kwargs)
