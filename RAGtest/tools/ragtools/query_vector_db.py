from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "rag_config.json"
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
    def __init__(
        self,
        model_name: str,
        local_files_only: bool = True,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        kwargs = {"local_files_only": local_files_only}
        if device:
            kwargs["device"] = device
        self.model = SentenceTransformer(model_name, **kwargs)

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

    def embed_query(self, input: str) -> list[float]:
        return self.embed_documents([input])[0]


class Timer:
    def __init__(self) -> None:
        self.started_at = time.perf_counter()
        self.last = self.started_at
        self.marks: list[tuple[str, float]] = []

    def mark(self, label: str) -> None:
        now = time.perf_counter()
        self.marks.append((label, now - self.last))
        self.last = now

    def total(self) -> float:
        return time.perf_counter() - self.started_at

    def print(self) -> None:
        for label, seconds in self.marks:
            print(f"{label}: {seconds:.3f}s", file=sys.stderr)
        print(f"total: {self.total():.3f}s", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    config = load_config()
    default_db_dir = configured_path(config, "vector_db_dir", DEFAULT_DB_DIR)
    default_collection = config.get("collection", DEFAULT_COLLECTION)
    default_model = config.get("embedding_model", DEFAULT_MODEL)

    parser = argparse.ArgumentParser(description="Query the local Chroma vector DB.")
    parser.add_argument("query", nargs="?", help="Question or search text.")
    parser.add_argument("--db-dir", type=Path, default=default_db_dir)
    parser.add_argument("--collection", default=default_collection)
    parser.add_argument("--model", default=default_model)
    parser.add_argument("--device", help="SentenceTransformer device, e.g. cpu or cuda.")
    parser.add_argument("-k", "--top-k", type=int, default=5)
    parser.add_argument(
        "--timing",
        action="store_true",
        help="Print load, embedding, and vector search timings to stderr.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Keep the model and collection loaded, then query repeatedly from stdin.",
    )
    return parser.parse_args()


def print_results(results: dict[str, object]) -> None:
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for index, (document, metadata, distance) in enumerate(
        zip(documents, metadatas, distances), start=1
    ):
        print(f"\n## Result {index}")
        print(f"score_distance: {distance:.4f}")
        print(f"source: {metadata.get('source_file')}")
        print(f"page: {metadata.get('page_number')}")
        print(document[:1200].strip())


def query_collection(
    collection,
    embedding_function: SentenceTransformerEmbeddingFunction,
    query: str,
    top_k: int,
    timing: bool,
) -> None:
    timer = Timer()
    query_embedding = embedding_function.embed_query(query)
    timer.mark("embed_query")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    timer.mark("vector_search")
    print_results(results)

    if timing:
        timer.print()


def main() -> None:
    configure_console_encoding()
    args = parse_args()
    if not args.interactive and not args.query:
        raise SystemExit("query is required unless --interactive is used")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    timer = Timer()
    embedding_function = SentenceTransformerEmbeddingFunction(args.model, device=args.device)
    timer.mark("load_model")
    client = chromadb.PersistentClient(path=str(args.db_dir))
    collection = client.get_collection(name=args.collection)
    timer.mark("open_collection")

    if args.timing:
        timer.print()

    if args.interactive:
        print("Interactive query mode. Press Ctrl+Z then Enter to exit.", file=sys.stderr)
        for line in sys.stdin:
            query = line.strip()
            if not query:
                continue
            query_collection(
                collection,
                embedding_function,
                query,
                top_k=args.top_k,
                timing=args.timing,
            )
            print("\n---", flush=True)
        return

    query_collection(
        collection,
        embedding_function,
        args.query,
        top_k=args.top_k,
        timing=args.timing,
    )


if __name__ == "__main__":
    main()
