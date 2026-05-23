import io
from pypdf import PdfReader


def extract_chunks(file_bytes: bytes, filename: str, chunk_size: int = 500, overlap: int = 50) -> list[dict]:
    """
    Extract text from a PDF and split into overlapping chunks.
    Returns list of {text, filename, page, chunk_index}.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    chunks = []
    chunk_index = 0

    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = text.strip()
        if not text:
            continue

        # Slide a window over the page text
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "filename": filename,
                    "page": page_num,
                    "chunk_index": chunk_index,
                })
                chunk_index += 1
            start += chunk_size - overlap

    return chunks
