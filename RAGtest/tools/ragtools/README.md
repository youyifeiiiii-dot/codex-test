# RAG Tools

Build the local vector database from Markdown files:

```powershell
python RAGtest\tools\ragtools\build_vector_db.py --reset
```

Query the local vector database:

```powershell
python RAGtest\tools\ragtools\query_vector_db.py "BBU是用来干嘛的" -k 3
```

Defaults:

- Source documents: `RAGtest\tools\pdftools\output`
- Vector database: `RAGtest\vectorstore\chroma`
- Embedding model: `BAAI/bge-small-zh-v1.5`

The Chroma database is generated locally and is intentionally not committed.
