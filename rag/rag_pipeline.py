import os
from groq import Groq
from dotenv import load_dotenv
from rag.vector_store import query_chunks

load_dotenv()

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


RAG_SYSTEM_PROMPT = """You are a helpful assistant that answers questions based strictly on the provided document excerpts.

Rules:
- Only use information from the provided excerpts to answer. Do not use outside knowledge.
- Always cite your sources using the format: [filename, page X]
- If the excerpts don't contain enough information to answer the question, say so clearly.
- Be concise and direct.
"""


def answer_question(user_id: str, question: str) -> dict:
    """
    Retrieve relevant chunks and generate an answer with citations.
    Returns {answer, sources, chunks_used} or {error}.
    """
    chunks = query_chunks(user_id, question, n_results=5)

    if not chunks:
        return {"error": "No documents found. Please upload a PDF first."}

    # Build context block
    context_parts = []
    for i, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"[Excerpt {i} — {chunk['filename']}, page {chunk['page']}]\n{chunk['text']}"
        )
    context = "\n\n".join(context_parts)

    user_message = f"""Document excerpts:
{context}

Question: {question}"""

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
        answer = response.choices[0].message.content.strip()

        # Deduplicate sources
        seen = set()
        sources = []
        for chunk in chunks:
            key = (chunk["filename"], chunk["page"])
            if key not in seen:
                seen.add(key)
                sources.append({"filename": chunk["filename"], "page": chunk["page"]})

        return {"answer": answer, "sources": sources, "chunks_used": len(chunks)}

    except Exception as e:
        return {"error": f"AI service error: {e}"}
