
"""RAG search for the Task 2 website style guide."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

# Resolve paths relative to this file, not the terminal's directory.
TASK_DIR = Path(__file__).resolve().parent
GROUP_DIR = TASK_DIR.parent
STYLE_DIR = TASK_DIR / "style_guide"
CACHE_DIR = TASK_DIR / ".rag_cache"

# Make the supplied common package importable.
sys.path.insert(0, str(GROUP_DIR))

load_dotenv(GROUP_DIR / ".env")

from common.llm_client import LLMClient, count_tokens  # noqa: E402


EMBEDDING_MODEL = "kiconnect.qwen3-embedding-8b"
MAX_OBSERVATION_TOKENS = 950


def chunk_text(text, chunk_size=160, overlap=30):
    """Split text into overlapping word chunks."""
    words = text.split()
    chunks = []
    step = chunk_size - overlap

    if step <= 0:
        raise ValueError("Overlap must be smaller than chunk_size.")

    for start in range(0, len(words), step):
        chunk = " ".join(words[start:start + chunk_size])
        if chunk:
            chunks.append(chunk)

        if start + chunk_size >= len(words):
            break

    return chunks


def load_documents():
    """Read Markdown files and return chunks with source names."""
    if not STYLE_DIR.is_dir():
        raise FileNotFoundError(f"Style guide folder missing: {STYLE_DIR}")

    documents = []

    for path in sorted(STYLE_DIR.rglob("*.md")):
        text = path.read_text(encoding="utf-8-sig")

        for number, chunk in enumerate(chunk_text(text), start=1):
            documents.append({
                "source": path.relative_to(STYLE_DIR).as_posix(),
                "chunk": number,
                "text": chunk,
            })

    if not documents:
        raise RuntimeError("No style-guide content found.")

    return documents


def normalize(vectors):
    """Normalize vectors for cosine similarity."""
    vectors = np.asarray(vectors, dtype=np.float32)
    lengths = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(lengths, 1e-12)


class StyleGuideRAG:
    def __init__(self, llm=None):
        self.llm = llm or LLMClient(
            embedding_model=EMBEDDING_MODEL,
            log_path=TASK_DIR / "logs" / "rag_llm.jsonl",
        )
        self.documents = load_documents()
        self.embeddings = self._load_or_build_embeddings()

    def _load_or_build_embeddings(self):
        """Reuse cached embeddings if the documents are unchanged."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        cache_file = CACHE_DIR / "embeddings.npz"
        fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "model": EMBEDDING_MODEL,
                    "documents": self.documents,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        if cache_file.exists():
            try:
                with np.load(cache_file, allow_pickle=False) as cache:
                    if str(cache["fingerprint"].item()) == fingerprint:
                        print("Loaded cached style-guide embeddings.")
                        return normalize(cache["vectors"])
            except (OSError, ValueError, KeyError):
                print("Embedding cache invalid; rebuilding.")

        print(f"Creating embeddings for {len(self.documents)} chunks...")

        texts = [doc["text"] for doc in self.documents]
        vectors = self.llm.embed(
            texts,
            model=EMBEDDING_MODEL,
            batch_size=32,
        )
        vectors = normalize(vectors)

        np.savez_compressed(
            cache_file,
            fingerprint=np.array(fingerprint),
            vectors=vectors,
        )

        print("Embeddings saved.")
        return vectors

    def search(self, query, k=3):
        """Return the k most relevant chunks with sources.

        The total returned style-guide observation is limited
        to 950 tokens, leaving room for tool metadata.
        """
        if not isinstance(query, str) or not query.strip():
            return []

        k = max(1, min(int(k), len(self.documents)))

        query_vector = normalize(
            self.llm.embed([query], model=EMBEDDING_MODEL)
        )[0]

        similarities = self.embeddings @ query_vector
        top_indices = np.argsort(similarities)[::-1][:k]

        results = []
        tokens_used = 0

        for index in top_indices:
            doc = self.documents[int(index)]
            header = (
                f"Source: {doc['source']} "
                f"(chunk {doc['chunk']})"
            )

            remaining = (
                MAX_OBSERVATION_TOKENS
                - tokens_used
                - count_tokens(header)
                - 10
            )

            if remaining <= 0:
                break

            text = doc["text"]

            # Truncate conservatively to fit the token budget.
            while text and count_tokens(text) > remaining:
                text = text[:max(0, int(len(text) * 0.85))]

            if not text:
                break

            result = {
                "source": doc["source"],
                "chunk": doc["chunk"],
                "text": text,
                "score": round(float(similarities[index]), 4),
            }
            results.append(result)

            tokens_used += count_tokens(
                json.dumps(result, ensure_ascii=False)
            ) + 5

        return results


_rag_instance = None


def search(query, k=3):
    """Convenience function for the agent's search_style_guide action."""
    global _rag_instance

    if _rag_instance is None:
        _rag_instance = StyleGuideRAG()

    return _rag_instance.search(query, k)


def main():
    documents = load_documents()
    sources = {doc["source"] for doc in documents}
    print(f"Style-guide documents: {len(sources)}")
    print(f"Total chunks: {len(documents)}")

    results = search("What are the rules for responsive layout?", k=3)

    for result in results:
        print(f"\nSource: {result['source']}")
        print(f"Similarity: {result['score']}")
        print(result["text"])


if __name__ == "__main__":
    main()
