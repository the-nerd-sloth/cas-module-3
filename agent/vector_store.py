"""
vector_store.py: builds and loads the local ChromaDB vector store.
"""
import os
import sqlite3

try:
    from langchain_chroma import Chroma
except ModuleNotFoundError as exc:
    raise SystemExit(
        "\n[ERROR] langchain-chroma is not installed.\n"
        "Fix:  pip install -r requirements.txt\n"
    ) from exc

from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from config import SQLITE_DB, VECTOR_DIR, EMBED_MODEL, CHUNK_SIZE, CHUNK_OVERLAP

console = Console()
_store  = None


def build_vector_store() -> Chroma:
    conn = sqlite3.connect(SQLITE_DB)
    cur  = conn.cursor()
    cur.execute("SELECT title, content, source_url, cancer_type FROM raw_documents")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        console.print("[yellow]Warning: no documents in DB yet. Run collect first.[/yellow]")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    docs = []
    for title, content, url, cancer_type in rows:
        if not content:
            continue
        for chunk in splitter.split_text(content):
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "title":       title or "",
                    "source_url":  url or "",
                    "cancer_type": cancer_type or "",
                },
            ))

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    os.makedirs(VECTOR_DIR, exist_ok=True)

    if not docs:
        console.print("[yellow]No chunks to embed — returning empty store.[/yellow]")
        return Chroma(persist_directory=VECTOR_DIR, embedding_function=embeddings)

    console.print(
        f"Building vector store from {len(rows)} documents ({len(docs)} chunks)..."
    )
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"Embedding {len(docs)} chunks...", total=len(docs)
        )
        store = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=VECTOR_DIR,
        )
        progress.update(task, completed=len(docs))

    console.print(f"[green]Vector store built — {len(docs)} chunks indexed.[/green]")
    return store


def get_vector_store() -> Chroma:
    global _store
    if _store is None:
        embeddings = OllamaEmbeddings(model=EMBED_MODEL)
        if os.path.exists(VECTOR_DIR) and os.listdir(VECTOR_DIR):
            _store = Chroma(
                persist_directory=VECTOR_DIR,
                embedding_function=embeddings,
            )
        else:
            _store = build_vector_store()
    return _store
