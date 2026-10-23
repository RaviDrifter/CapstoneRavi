from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any
from .config import DOCS_PATH, RETRIEVAL_BACKEND, CHROMA_PATH, EMBEDDING_MODEL, RETRIEVAL_MIN_SCORE

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False

class KnowledgeRetriever:
    """Persistent-corpus retriever. TF-IDF is the portable offline default; Chroma is optional."""
    def __init__(self, docs_path: Path = DOCS_PATH, backend: str = RETRIEVAL_BACKEND):
        self.docs_path = Path(docs_path)
        self.backend = backend
        self.documents = json.loads(self.docs_path.read_text(encoding="utf-8"))
        self.passages: list[dict[str, Any]] = []
        for doc in self.documents:
            content = str(doc.get("content", ""))
            chunks = self._chunk(content, max_chars=1100, overlap=160)
            for i, chunk in enumerate(chunks):
                self.passages.append({
                    "passage_id": f"{doc.get('doc_id', 'DOC-UNKNOWN')}::chunk-{i:03d}",
                    "doc_id": str(doc.get("doc_id", "DOC-UNKNOWN")),
                    "title": str(doc.get("title", "Untitled")),
                    "category": str(doc.get("category", "unknown")),
                    "chunk_index": i,
                    "content": chunk,
                })
        self.vectorizer = None
        self.matrix = None
        if SKLEARN_AVAILABLE and self.passages:
            self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), strip_accents="unicode", sublinear_tf=True, stop_words="english")
            self.matrix = self.vectorizer.fit_transform([p["content"] for p in self.passages])
        self._chroma = None
        if backend == "chroma":
            self._init_chroma()

    @staticmethod
    def _chunk(text: str, max_chars: int = 1100, overlap: int = 160) -> list[str]:
        text = text.strip()
        if not text:
            return []
        # Prefer section/paragraph boundaries, then enforce a bounded passage size.
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks, current = [], ""
        for para in paragraphs:
            if len(para) > max_chars:
                if current:
                    chunks.append(current); current = ""
                start = 0
                while start < len(para):
                    chunks.append(para[start:start + max_chars])
                    if start + max_chars >= len(para): break
                    start += max_chars - overlap
                continue
            candidate = f"{current}\n\n{para}".strip()
            if len(candidate) > max_chars and current:
                chunks.append(current)
                current = (current[-overlap:] + "\n\n" + para).strip() if overlap else para
            else:
                current = candidate
        if current:
            chunks.append(current)
        return chunks

    def _init_chroma(self):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            self._chroma_client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            self._chroma = self._chroma_client.get_or_create_collection("cloudserve_docs_v1")
            # Rebuild deterministically so the collection matches the current corpus.
            existing = self._chroma.get(include=[])
            if existing.get("ids"):
                self._chroma.delete(ids=existing["ids"])
            for start in range(0, len(self.passages), 64):
                batch = self.passages[start:start + 64]
                embeddings = self._embedding_model.encode([p["content"] for p in batch]).tolist()
                self._chroma.add(
                    ids=[p["passage_id"] for p in batch],
                    documents=[p["content"] for p in batch],
                    metadatas=[{k: p[k] for k in ("doc_id", "title", "category", "chunk_index")} for p in batch],
                    embeddings=embeddings,
                )
        except Exception:
            # Failure to download/init an optional embedding stack should not block the harness.
            self._chroma = None

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        query = (query or "").strip()
        if not query:
            return []
        if self._chroma is not None:
            try:
                emb = self._embedding_model.encode([query]).tolist()
                res = self._chroma.query(query_embeddings=emb, n_results=min(top_k, len(self.passages)), include=["documents", "metadatas", "distances"])
                out = []
                for i, content in enumerate(res["documents"][0]):
                    meta = res["metadatas"][0][i]
                    distance = float(res["distances"][0][i])
                    out.append({"passage_id": res["ids"][0][i], **meta, "content": content, "score": round(max(0.0, 1.0-distance), 4)})
                return [x for x in out if x["score"] >= RETRIEVAL_MIN_SCORE]
            except Exception:
                pass
        if self.vectorizer is None or self.matrix is None:
            terms = set(re.findall(r"[a-z0-9_]+", query.lower()))
            scored = []
            for p in self.passages:
                body = p["content"].lower()
                score = len(terms.intersection(set(re.findall(r"[a-z0-9_]+", body)))) / max(1, len(terms))
                if score > 0:
                    scored.append((score, p))
        else:
            qv = self.vectorizer.transform([query])
            sims = cosine_similarity(qv, self.matrix).ravel()
            scored = [(float(sims[i]), p) for i, p in enumerate(self.passages) if sims[i] > 0]
        scored.sort(key=lambda x: (-x[0], x[1]["passage_id"]))
        out = []
        for score, p in scored[:top_k]:
            # Scores are lexical relevance values, not calibrated probabilities.
            if score < RETRIEVAL_MIN_SCORE:
                continue
            out.append({**p, "score": round(float(score), 4)})
        return out

_retriever: KnowledgeRetriever | None = None

def get_retriever() -> KnowledgeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever()
    return _retriever
