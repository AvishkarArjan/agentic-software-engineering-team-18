"""Token-aware chunking and R1--R5 retrieval without frameworks."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import time

import numpy as np
from rank_bm25 import BM25Okapi
import tiktoken

ENC = tiktoken.get_encoding('cl100k_base')


def tokens(text):
    return ENC.encode(text, disallowed_special=())


def lexical_tokens(text):
    # Keep exact dotted settings / hyphenated error codes AND their components.
    terms = re.findall(r'[a-z0-9]+(?:[_.-][a-z0-9]+)*', text.lower())
    return terms + [part for term in terms if re.search(r'[_.-]', term)
                    for part in re.split(r'[_.-]', term)]


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str


def recursive_units(text, budget, level=0):
    """Prefer heading, paragraph, then sentence boundaries; token-split last."""
    if len(tokens(text)) <= budget:
        return [text]
    patterns = [r'(?m)(?=^#{1,6} )', r'\n\s*\n', r'(?<=[.!?])\s+']
    if level == len(patterns):
        ids = tokens(text)
        return [ENC.decode(ids[i:i + budget]) for i in range(0, len(ids), budget)]
    pieces = [p for p in re.split(patterns[level], text) if p.strip()]
    return [unit for p in pieces for unit in recursive_units(p, budget, level + 1)]


def chunk_corpus(documents, size=220, overlap=32, recursive=True):
    if size < 80 or not 0 <= overlap < size // 2:
        raise ValueError('size >= 80 and 0 <= overlap < size/2 required')
    chunks = []
    for doc in documents:
        header = f"[{doc['doc_id']}] {doc['type']} | {doc['title']} | version {doc['version']}\n"
        budget = size - len(tokens(header)) - 2
        if budget <= overlap:
            raise ValueError('Metadata leaves insufficient chunk capacity')
        bodies = []
        if not recursive:
            ids = tokens(doc['text'])
            for start in range(0, len(ids), budget - overlap):
                bodies.append(ENC.decode(ids[start:start + budget]))
                if start + budget >= len(ids):
                    break
        else:
            # Units reserve overlap capacity, allowing the previous chunk's tail
            # to be retained without exceeding the configured token ceiling.
            units = recursive_units(doc['text'], budget - overlap)
            current = ''
            for unit in units:
                candidate = (current + '\n\n' + unit).strip()
                if current and len(tokens(candidate)) > budget:
                    bodies.append(current)
                    tail = ENC.decode(tokens(current)[-overlap:]) if overlap else ''
                    current = (tail + '\n\n' + unit).strip()
                    while len(tokens(current)) > budget and tail:
                        tail = tail[1:]
                        current = (tail + '\n\n' + unit).strip()
                else:
                    current = candidate
            if current:
                bodies.append(current)
        for i, body in enumerate(bodies):
            chunk = Chunk(f"{doc['doc_id']}:{i}", doc['doc_id'], header + body)
            assert len(tokens(chunk.text)) <= size, chunk.chunk_id
            chunks.append(chunk)
    return chunks


def normalize(matrix):
    matrix = np.asarray(matrix, dtype=np.float32)
    if matrix.ndim != 2 or not np.isfinite(matrix).all():
        raise ValueError('Invalid embedding matrix')
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError('Zero embedding vector')
    return matrix / norms


def scale(scores):
    scores = np.asarray(scores, dtype=np.float64)
    span = np.ptp(scores)
    return (scores - scores.min()) / span if span > 0 else np.zeros_like(scores)


class Retriever:
    def __init__(self, chunks, vectors=None):
        self.chunks = chunks
        self.bm25 = BM25Okapi([lexical_tokens(c.text) for c in chunks])
        self.vectors = normalize(vectors) if vectors is not None else None

    def scores(self, query, vector=None, mode='hybrid', alpha=.5):
        lexical = self.bm25.get_scores(lexical_tokens(query))
        if mode == 'bm25':
            return lexical
        dense = self.vectors @ vector
        if mode == 'dense':
            return dense
        return alpha * scale(lexical) + (1 - alpha) * scale(dense)

    def retrieve(self, query, vector=None, mode='hybrid', alpha=.5, rewritten=None,
                 rewrite_vector=None, k=5):
        scores = self.scores(query, vector, mode, alpha)
        if rewritten is not None:
            scores = (scores + self.scores(rewritten, rewrite_vector, mode, alpha)) / 2
        order = np.argsort(-scores, kind='stable')
        # One representative chunk per document: evaluation is at document level.
        seen, result = set(), []
        for i in order:
            c = self.chunks[i]
            if c.doc_id not in seen:
                result.append({'doc_id': c.doc_id, 'chunk_id': c.chunk_id,
                               'text': c.text, 'score': float(scores[i])})
                seen.add(c.doc_id)
                if len(result) == k:
                    break
        return result


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows), encoding='utf-8')
