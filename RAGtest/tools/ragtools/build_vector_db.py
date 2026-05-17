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
MANIFEST_NAME = ".vector_manifest.json"


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


def load_manifest(db_dir: Path) -> dict[str, dict[str, object]]:
    manifest_path = db_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return {}
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def save_manifest(db_dir: Path, manifest: dict[str, dict[str, object]]) -> None:
    db_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = db_dir / MANIFEST_NAME
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def file_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def markdown_paths(docs_dir: Path) -> list[Path]:
    return sorted(docs_dir.glob("*.md"))


def chunks_for_file(
    md_path: Path, chunk_size: int, overlap: int
) -> tuple[list[str], list[str], list[dict[str, str | int]]]:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []

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


def load_markdown_chunks(
    md_paths: list[Path], chunk_size: int, overlap: int
) -> tuple[list[str], list[str], list[dict[str, str | int]], dict[str, int]]:
    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, str | int]] = []
    chunk_counts: dict[str, int] = {}

    for md_path in md_paths:
        file_ids, file_documents, file_metadatas = chunks_for_file(
            md_path, chunk_size=chunk_size, overlap=overlap
        )
        ids.extend(file_ids)
        documents.extend(file_documents)
        metadatas.extend(file_metadatas)
        chunk_counts[str(md_path.resolve())] = len(file_documents)

    return ids, documents, metadatas, chunk_counts


def collection_has_file_chunks(collection, md_path: Path, expected_chunks: int) -> bool:
    if expected_chunks == 0:
        return False
    result = collection.get(where={"source_file": md_path.name}, include=[])
    return len(result.get("ids", [])) == expected_chunks


def plan_incremental_files(
    md_paths: list[Path],
    manifest: dict[str, dict[str, object]],
    collection,
    chunk_size: int,
    overlap: int,
) -> tuple[list[Path], dict[str, dict[str, object]], int]:
    files_to_index: list[Path] = []
    next_manifest: dict[str, dict[str, object]] = {}
    skipped = 0

    for md_path in md_paths:
        source_key = str(md_path.resolve())
        fingerprint = file_fingerprint(md_path)
        existing = manifest.get(source_key, {})
        chunk_count = int(existing.get("chunk_count", 0) or 0)

        if not chunk_count:
            chunk_count = len(
                chunk_text(
                    md_path.read_text(encoding="utf-8"),
                    chunk_size=chunk_size,
                    overlap=overlap,
                )
            )

        if (
            existing.get("fingerprint") == fingerprint
            and existing.get("chunk_size") == chunk_size
            and existing.get("overlap") == overlap
            and collection_has_file_chunks(collection, md_path, chunk_count)
        ):
            next_manifest[source_key] = existing
            skipped += 1
            continue

        if (
            not existing
            and collection_has_file_chunks(collection, md_path, chunk_count)
        ):
            next_manifest[source_key] = {
                "fingerprint": fingerprint,
                "source_file": md_path.name,
                "chunk_count": chunk_count,
                "chunk_size": chunk_size,
                "overlap": overlap,
            }
            skipped += 1
            continue

        files_to_index.append(md_path)
        next_manifest[source_key] = {
            "fingerprint": fingerprint,
            "source_file": md_path.name,
            "chunk_count": chunk_count,
            "chunk_size": chunk_size,
            "overlap": overlap,
        }

    return files_to_index, next_manifest, skipped


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
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--reset", action="store_true", help="Delete the DB first.")
    return parser.parse_args()


def main() -> None:
    configure_console_encoding()
    args = parse_args()

    if not args.docs_dir.exists():
        raise FileNotFoundError(f"Docs directory not found: {args.docs_dir}")

    if args.reset and args.db_dir.exists():
        print(f"Removing existing DB: {args.db_dir}", flush=True)
        shutil.rmtree(args.db_dir)

    args.db_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(args.db_dir))
    collection = client.get_or_create_collection(
        name=args.collection,
        metadata={"hnsw:space": "cosine", "embedding_model": args.model},
    )

    print(f"Loading Markdown from: {args.docs_dir}", flush=True)
    md_paths = markdown_paths(args.docs_dir)
    if not md_paths:
        raise SystemExit(f"No Markdown content found in: {args.docs_dir}")

    manifest = load_manifest(args.db_dir)
    current_keys = {str(path.resolve()) for path in md_paths}
    stale_entries = [
        entry
        for source_key, entry in manifest.items()
        if source_key not in current_keys and isinstance(entry, dict)
    ]
    for entry in stale_entries:
        source_file = entry.get("source_file")
        if isinstance(source_file, str):
            collection.delete(where={"source_file": source_file})
            print(f"Removed stale vectors: {source_file}", flush=True)

    files_to_index, next_manifest, skipped = plan_incremental_files(
        md_paths,
        manifest,
        collection,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    print(
        f"Markdown files: {len(md_paths)} total, {skipped} unchanged, "
        f"{len(files_to_index)} to index",
        flush=True,
    )
    if not files_to_index:
        save_manifest(args.db_dir, next_manifest)
        print(f"Nothing new to index. Persisted at: {args.db_dir}")
        return

    ids, documents, metadatas, chunk_counts = load_markdown_chunks(
        files_to_index, chunk_size=args.chunk_size, overlap=args.overlap
    )
    if not documents:
        raise SystemExit(f"No changed Markdown content found in: {args.docs_dir}")

    for md_path in files_to_index:
        collection.delete(where={"source_file": md_path.name})

    for md_path in files_to_index:
        source_key = str(md_path.resolve())
        next_manifest[source_key]["chunk_count"] = chunk_counts[source_key]

    source_count = len(set(m["source_file"] for m in metadatas))
    print(f"Prepared {len(documents)} chunks from {source_count} changed files", flush=True)
    print(f"Loading embedding model: {args.model}", flush=True)

    embedding_function = SentenceTransformerEmbeddingFunction(args.model)
    collection = client.get_or_create_collection(
        name=args.collection,
        embedding_function=embedding_function,
        metadata={"hnsw:space": "cosine", "embedding_model": args.model},
    )

    batch_size = args.batch_size
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        current = min(end, len(documents))
        print(f"Indexed {current}/{len(documents)} chunks", flush=True)

    save_manifest(args.db_dir, next_manifest)
    print(f"Built collection: {args.collection}")
    print(f"Documents: {len(documents)} chunks from {source_count} changed files")
    print(f"Persisted at: {args.db_dir}")


if __name__ == "__main__":
    main()
