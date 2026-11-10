"""
main.py: entry point for the Cancer AI Agent

Usage:
    python main.py collect          # fetch all data + build vector store (one-time run)
    python main.py chat             # interactive multi-turn session
    python main.py ask "QUESTION"   # single question
    python main.py build-index      # rebuild vector store without re-fetching data
"""
import argparse
import os
import shutil

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

console = Console()


def cmd_collect(args):
    """Re-fetch all data from WHO GHO, World Bank, Wikipedia, then build vector store."""
    from config import SQLITE_DB, VECTOR_DIR

    if os.path.exists(SQLITE_DB):
        os.remove(SQLITE_DB)
        console.print("[dim]Removed old database.[/dim]")
    if os.path.exists(VECTOR_DIR):
        shutil.rmtree(VECTOR_DIR)
        console.print("[dim]Removed old vector store.[/dim]")

    from data_collector import run_data_collection
    run_data_collection()

    from vector_store import build_vector_store
    build_vector_store()

    console.print("\n[bold green]Setup complete. Run: python main.py chat[/bold green]")


def cmd_build_index(args):
    """Rebuild vector store from the existing database (no re-fetching)."""
    from config import VECTOR_DIR

    if os.path.exists(VECTOR_DIR):
        shutil.rmtree(VECTOR_DIR)
        console.print("[dim]Removed old vector store.[/dim]")

    from vector_store import build_vector_store
    build_vector_store()


def cmd_ask(args):
    """Answer a single question and exit."""
    from agent import ask

    answer = ask(args.question)
    console.print(
        Panel(answer, title="[bold green]Answer[/bold green]", expand=False)
    )


def cmd_chat(args):
    """Interactive multi-turn chat session."""
    from agent import ask
    from config import LLM_MODEL

    console.print(Panel(
        f"[bold cyan]Cancer AI Agent[/bold cyan]  |  model: [yellow]{LLM_MODEL}[/yellow]\n"
        "Ask anything about cancer statistics, mortality, incidence, survival.\n"
        "[dim]Commands:  exit / quit: end session  |  clear: reset history[/dim]",
        expand=False,
    ))

    history = []
    while True:
        try:
            question = Prompt.ask("\n[bold yellow]You[/bold yellow]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if question.lower() == "clear":
            history = []
            console.print("[dim]History cleared.[/dim]")
            continue

        try:
            answer = ask(question, history=history)
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")
            continue

        console.print(f"\n[bold green]Agent:[/bold green] {answer}")

        history.append(("user",  question))
        history.append(("agent", answer))
        # Keep last 10 turns to avoid context length overflow
        if len(history) > 20:
            history = history[-20:]


def main():
    parser = argparse.ArgumentParser(
        prog="cancer-agent",
        description="Agentic AI for cancer statistics: runs locally via Ollama",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser(
        "collect",
        help="Fetch all data from WHO GHO, World Bank, Wikipedia and build vector store",
    )
    sub.add_parser(
        "build-index",
        help="Rebuild ChromaDB vector store from existing database (no re-fetch)",
    )
    p_ask = sub.add_parser("ask", help="Answer a single question")
    p_ask.add_argument("question", type=str)

    sub.add_parser("chat", help="Start interactive chat session")

    args = parser.parse_args()
    dispatch = {
        "collect":     cmd_collect,
        "build-index": cmd_build_index,
        "ask":         cmd_ask,
        "chat":        cmd_chat,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
