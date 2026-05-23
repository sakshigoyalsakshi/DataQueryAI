import os
import chromadb
from chromadb.config import Settings


def _get_chroma_path() -> str:
    base = os.getenv("DB_PATH", "/data/app.db")
    return os.path.join(os.path.dirname(base), "chroma_db")


def _get_client() -> chromadb.PersistentClient:
    path = _get_chroma_path()
    os.makedirs(path, exist_ok=True)
    return chromadb.PersistentClient(path=path)


def get_collection(user_id: str) -> chromadb.Collection:
    client = _get_client()
    # One collection per user; chromadb creates it if missing
    return client.get_or_create_collection(
        name=f"user_{user_id[:8]}",
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(user_id: str, chunks: list[dict], doc_id: str) -> None:
    """Store chunks in the user's collection. doc_id is used to namespace chunks."""
    collection = get_collection(user_id)
    ids = [f"{doc_id}_{c['chunk_index']}" for c in chunks]
    documents = [c["text"] for c in chunks]
    metadatas = [
        {"filename": c["filename"], "page": c["page"], "chunk_index": c["chunk_index"]}
        for c in chunks
    ]
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)


def query_chunks(user_id: str, question: str, n_results: int = 5) -> list[dict]:
    """Return top-n most relevant chunks for the question."""
    collection = get_collection(user_id)
    if collection.count() == 0:
        return []
    results = collection.query(query_texts=[question], n_results=min(n_results, collection.count()))
    chunks = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        chunks.append({"text": doc, "filename": meta["filename"], "page": meta["page"]})
    return chunks


def delete_doc_chunks(user_id: str, doc_id: str, num_chunks: int) -> None:
    """Remove all chunks for a specific document."""
    collection = get_collection(user_id)
    ids = [f"{doc_id}_{i}" for i in range(num_chunks)]
    existing = collection.get(ids=ids)["ids"]
    if existing:
        collection.delete(ids=existing)
