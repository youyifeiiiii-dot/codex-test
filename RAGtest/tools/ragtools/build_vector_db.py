from __future__ import annotations

import argparse
import hashlib
import json
import sys
import re
import shutil
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "rag_config.json"
DEFAULT_DOCS_DIR = PROJECT_ROOT / "tools" / "pdftools" / "output"
DEFAULT_DB_DIR = PROJECT_ROOT / "vectorstore" / "chroma"
DEFAULT_COLLECTION = "oceanstor_dorado_docs"
DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


def configure_console_encoding() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def load_config() -> dict[str, str]:
    if not CONFIG_PATH.exists():
        return {}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def configured_path(config: dict[str, str], key: str, fallback: Path) -> Path:
    value = config.get(key)
    return Path(value) if value else fallback


class SentenceTransformerEmbeddingFunction:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def name(self) -> str:
        return f"sentence-transformers:{self.model_name}"

    def __call__(self, input: list[str]) -> list[list[float]]:
        return self.embed_documents(input)

    def embed_documents(self, input: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            input,
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self.embed_documents(input)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [chunk for chunk in chunks if chunk]


def page_number_from_name(path: Path) -> int | None:
    match = re.search(r"_page_(\d+)\.md$", path.name)
    return int(match.group(1)) if match else None


def document_id(path: Path, chunk_index: int) -> str:
    raw = f"{path.as_posix()}::{chunk_index}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def load_markdown_chunks(
    docs_dir: Path, chunk_size: int, overlap: int
) -> tuple[list[str], list[str], list[dict[str, str | int]]]:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

    for md_path in sorted(docs_dir.glob("*.md")):
        text = md_path.read_text(encoding="utf-8")
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        page_number = page_number_from_name(md_path)

        for chunk_index, chunk in enumerate(chunks):
            ids.append(document_id(md_path, chunk_index))
            documents.append(chunk)
            metadatas.append(
                {
                    "source_file": md_path.name,
                    "source_path": str(md_path),
                    "page_number": page_number or 0,
                    "chunk_index": chunk_index,
                }
            )

    return ids, documents, metadatas


def parse_args() -> argparse.Namespace:
    config = load_config()
    default_docs_dir = configured_path(config, "output_dir", DEFAULT_DOCS_DIR)
    default_db_dir = configured_path(config, "vector_db_dir", DEFAULT_DB_DIR)
    default_collection = config.get("collection", DEFAULT_COLLECTION)
    default_model = config.get("embedding_model", DEFAULT_MODEL)

    parser = argparse.ArgumentParser(description="Build a local Chroma vector DB.")
    parser.add_argument("--docs-dir", type=Path, default=default_docs_dir)
    parser.add_argument("--db-dir", type=Path, default=default_db_dir)
    parser.add_argument("--collection", default=default_collection)
    parser.add_argument("--model", default=default_model)
    parser.add_argument("--chunk-size", type=int, default=900)
    parser.add_argument("--overlap", type=int, default=120)
    parser.add_argument("--reset", action="store_true", help="Delete the DB first.")
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()

    if not args.docs_dir.exists():
        raise FileNotFoundError(f"Docs directory not found: {args.docs_dir}")

    if args.reset and args.db_dir.exists():
        shutil.rmtree(args.db_dir)

    ids, documents, metadatas = load_markdown_chunks(
        args.docs_dir, chunk_size=args.chunk_size, overlap=args.overlap
    )
    if not documents:
        raise SystemExit(f"No Markdown content found in: {args.docs_dir}")

    args.db_dir.mkdir(parents=True, exist_ok=True)
    embedding_function = SentenceTransformerEmbeddingFunction(args.model)
    client = chromadb.PersistentClient(path=str(args.db_dir))
    collection = client.get_or_create_collection(
        name=args.collection,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine", "embedding_model": args.model},
    )

    batch_size = 64
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    print(f"Built collection: {args.collection}")
    print(f"Documents: {len(documents)} chunks from {len(set(m['source_file'] for m in metadatas))} files")
    print(f"Persisted at: {args.db_dir}")


if __name__ == "__main__":
    main()
