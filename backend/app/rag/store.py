"""Local RAG store: PDF -> chunks -> MiniLM embeddings -> ChromaDB.

Embeddings use ChromaDB's built-in DefaultEmbeddingFunction, which runs the
all-MiniLM-L6-v2 model via ONNX Runtime (~80MB) — no torch/transformers needed.
Heavy imports are loaded lazily so the API starts before the model is downloaded.
"""
import logging
import os
import re
import uuid

from app.config import settings

logger = logging.getLogger(__name__)

# ChromaDB 0.5.x posthog telemetry emits harmless errors on Windows; silence them.
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)

_client = None
_collection = None
_COLLECTION = "manuals"


def _get_collection():
    global _client, _collection
    if _collection is None:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
        from chromadb.utils import embedding_functions

        os.makedirs(settings.chroma_dir, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        ef = embedding_functions.DefaultEmbeddingFunction()  # all-MiniLM-L6-v2 (ONNX)
        _collection = _client.get_or_create_collection(_COLLECTION, embedding_function=ef)
    return _collection


def _split_text(text: str, chunk_size: int = 800, overlap: int = 120) -> list[str]:
    """Lightweight recursive splitter on paragraph/sentence boundaries."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    pieces = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if len(current) + len(piece) + 1 <= chunk_size:
            current = f"{current} {piece}".strip()
        else:
            if current:
                chunks.append(current)
            # carry overlap from the tail of the previous chunk
            current = (current[-overlap:] + " " + piece).strip() if current else piece
            while len(current) > chunk_size:
                chunks.append(current[:chunk_size])
                current = current[chunk_size - overlap:]
    if current:
        chunks.append(current)
    return chunks


# A heading looks like "2. Vibration Thresholds" / "3.1 Relief Valve" or a short
# ALL-CAPS / Title-Case line. Used to tag chunks with the section they belong to.
_NUMBERED_HEADING = re.compile(r"(?m)^\s*(\d+(?:\.\d+)*\.?\s+[A-Z][^\n]{2,70})\s*$")
_HEADING_INLINE = re.compile(r"(\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z][^\n]{2,70}?)(?=\s+[A-Z][a-z]|\s*$)")


def _segment_by_heading(text: str, current: str | None):
    """Split a page into (section_title, body) segments, carrying the last-seen
    heading across page boundaries via `current`."""
    # Split on numbered headings, keeping the heading as a delimiter.
    parts = re.split(_NUMBERED_HEADING, text)
    segments: list[tuple[str | None, str]] = []
    if parts[0].strip():
        segments.append((current, parts[0]))
    # parts now alternates: [pre, heading, body, heading, body, ...]
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""
        current = heading
        segments.append((heading, body))
    return segments, current


def ingest_pdf(pdf_path: str, source_name: str) -> int:
    """Chunk + embed a PDF into Chroma, tagging each chunk with its section.

    Returns the number of chunks stored."""
    from pypdf import PdfReader

    reader = PdfReader(pdf_path)
    documents: list[str] = []
    metadatas: list[dict] = []
    current_section: str | None = None
    for page_num, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if not text:
            continue
        segments, current_section = _segment_by_heading(text, current_section)
        for section, body in segments:
            for chunk in _split_text(body):
                documents.append(chunk)
                metadatas.append(
                    {"source": source_name, "page": page_num, "section": section or ""}
                )

    if not documents:
        return 0

    collection = _get_collection()
    ids = [f"{source_name}-{uuid.uuid4().hex}" for _ in documents]
    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(documents)


def retrieve(query: str, k: int = 4) -> list[dict]:
    """Return up to k relevant chunks as {source, snippet, page}."""
    try:
        collection = _get_collection()
        if collection.count() == 0:
            return []
        res = collection.query(query_texts=[query], n_results=k)
    except Exception as exc:
        logger.warning("RAG retrieval failed: %s", exc)
        return []

    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out = []
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        dist = dists[i] if i < len(dists) else None
        out.append(
            {
                "source": meta.get("source", "manual"),
                "page": meta.get("page"),
                "section": meta.get("section") or None,
                "snippet": doc.strip()[:500],
                "score": round(1.0 / (1.0 + dist), 3) if dist is not None else None,
            }
        )
    return out


def delete_source(source_name: str) -> None:
    """Remove all chunks for a given manual from the vector store."""
    try:
        _get_collection().delete(where={"source": source_name})
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to delete chroma source %s: %s", source_name, exc)


def reset_store() -> None:
    """Drop the entire manuals collection (used by the data reset)."""
    global _client, _collection
    try:
        if _client is None:
            _get_collection()
        _client.delete_collection(_COLLECTION)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to reset chroma store: %s", exc)
    finally:
        _collection = None


def format_context(chunks: list[dict]) -> str:
    """Render retrieved chunks into a prompt-ready block."""
    blocks = []
    for c in chunks:
        section = f" §{c['section']}" if c.get("section") else ""
        page = f", p.{c['page']}" if c.get("page") else ""
        blocks.append(f"[{c['source']}{section}{page}] {c['snippet']}")
    return "\n\n".join(blocks)
