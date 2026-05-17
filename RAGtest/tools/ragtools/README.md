# RAG Tools

Build the local vector database from Markdown files:

```powershell
python RAGtest\tools\ragtools\build_vector_db.py
```

Rebuild the local vector database from scratch:

```powershell
python RAGtest\tools\ragtools\build_vector_db.py --reset
```

Query the local vector database:

```powershell
python RAGtest\tools\ragtools\query_vector_db.py "What is BBU used for?" -k 3
```

Defaults:

- Source documents: `RAGtest\tools\pdftools\output`
- Vector database: `RAGtest\vectorstore\chroma`
- Embedding model: `BAAI/bge-small-zh-v1.5`

Incremental behavior:

- `pdf2MD.py` writes `.pdf2md_manifest.json` in the Markdown output folder and skips unchanged source files.
- Before reusing the conversion workflow for a fresh batch, clear `.pdf2md_manifest.json` first:

```powershell
Remove-Item C:\LLM-Study\RAG-runtime-files\output\.pdf2md_manifest.json -ErrorAction SilentlyContinue
```

- `build_vector_db.py` writes `.vector_manifest.json` in the Chroma database folder and only indexes changed Markdown files.

The Chroma database is generated locally and is intentionally not committed.
