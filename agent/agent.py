"""
agent.py: LangGraph agentic loop
Graph: START -> agent_node <-> tool_node -> END
"""
from typing import Annotated, TypedDict, Literal

from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, BaseMessage, ToolMessage
)
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from config import LLM_MODEL, OLLAMA_BASE_URL, MAX_SEARCH_ITERATIONS
from tools import ALL_TOOLS

# System prompt — strict tool-execution mandate

SYSTEM_PROMPT = """You are an oncology data analyst. You have direct access to a
local cancer statistics database via tools. Your ONLY job is to use those tools
and report the actual results.

CRITICAL RULES — you MUST follow these without exception:
1. NEVER describe, explain, or show SQL queries in your reply.
2. NEVER say what you "would" do or "could" do.
3. ALWAYS call a tool immediately to get real data, then report the actual numbers.
4. If a question can be answered with run_custom_sql, call it NOW and return the result.
5. Your reply must contain actual numbers from tool output, not hypothetical queries.

Tools available:
  run_custom_sql              — execute any SELECT against the local SQLite database
  query_cancer_profiles       — Wikipedia profiles: overview, risk factors, survival
  query_who_statistics        — WHO GHO cancer death rates by country/year/sex
  query_worldbank_statistics  — World Bank NCD mortality with male/female split
  list_available_cancer_types — list all cancer types in the database
  list_available_countries    — list all countries in WHO and World Bank tables
  semantic_search             — meaning-based search across all documents

Decision logic — use this EVERY TIME:
  "How many records?" or counting questions  -> run_custom_sql immediately
  Cancer biology / risk factors / prognosis  -> query_cancer_profiles
  Mortality by gender over time              -> query_worldbank_statistics
  Age-standardised death rates by country    -> query_who_statistics
  What data exists?                          -> list_available_cancer_types or list_available_countries
  Complex multi-table question               -> run_custom_sql

Example of CORRECT behaviour:
  User: "How many records do you have?"
  You: [call run_custom_sql with "SELECT COUNT(*) FROM who_statistics"] -> report the number

Example of FORBIDDEN behaviour:
  User: "How many records do you have?"
  You: "I can use this SQL query: SELECT COUNT(*) ..."  <- NEVER DO THIS
"""

FORCE_TOOL_REMINDER = """You described a query but did not call any tool.
You MUST call a tool RIGHT NOW. Do not write any more text — just call the tool."""

# Helpers

_SQL_MARKERS = ("select ", "```sql", "i can use", "i would", "i could",
                "the query", "this query", "following query", "following sql")

def _looks_like_narration(text: str) -> bool:
    """Return True if the model described a tool call instead of executing one."""
    low = text.lower()
    return any(m in low for m in _SQL_MARKERS)


# Agent state

class AgentState(TypedDict):
    messages:    Annotated[list[BaseMessage], add_messages]
    iterations:  int
    forced:      bool   # True if we already injected a force-tool reminder


# Graph

def build_agent():
    llm = ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0,          # deterministic — better tool discipline
        num_predict=1024,       # cap generation length
    ).bind_tools(ALL_TOOLS)

    tool_node = ToolNode(ALL_TOOLS)

    def agent_node(state: AgentState):
        msgs = list(state["messages"])

        # Inject system prompt if not present
        if not any(isinstance(m, SystemMessage) for m in msgs):
            msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs

        response   = llm.invoke(msgs)
        iterations = state.get("iterations", 0) + 1
        forced     = state.get("forced", False)

        # Detect narration without tool call and inject a strong nudge (once)
        content = response.content or ""
        if (
            isinstance(response, AIMessage)
            and not response.tool_calls
            and _looks_like_narration(content)
            and not forced
        ):
            nudge = HumanMessage(content=FORCE_TOOL_REMINDER)
            msgs  = msgs + [response, nudge]
            response2 = llm.invoke(msgs)
            return {
                "messages":   [response, nudge, response2],
                "iterations": iterations + 1,
                "forced":     True,
            }

        return {
            "messages":   [response],
            "iterations": iterations,
            "forced":     forced,
        }

    def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
        last = state["messages"][-1]
        if state.get("iterations", 0) >= MAX_SEARCH_ITERATIONS:
            return END
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", END: END}
    )
    graph.add_edge("tools", "agent")
    return graph.compile()


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = build_agent()
    return _agent


def ask(question: str, history: list | None = None) -> str:
    agent = get_agent()
    msgs: list[BaseMessage] = []
    if history:
        for role, content in history:
            msgs.append(
                HumanMessage(content=content)
                if role == "user"
                else AIMessage(content=content)
            )
    msgs.append(HumanMessage(content=question))

    result = agent.invoke({"messages": msgs, "iterations": 0, "forced": False})

    # Find last AIMessage that is not a tool-call request and has real content
    for msg in reversed(result["messages"]):
        if (
            isinstance(msg, AIMessage)
            and not msg.tool_calls
            and msg.content
            and not _looks_like_narration(msg.content)
        ):
            return msg.content

    # Fallback: return whatever the last message has
    last = result["messages"][-1]
    return getattr(last, "content", str(last))
