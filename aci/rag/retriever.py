"""
Retriever (§9, §16).

Hybrid retrieval: a dependency-free TF-IDF cosine channel (always available,
zero setup) fused with a dense-embedding channel over locally-computed Ollama
embeddings (used automatically when reachable, skipped cleanly when not — see
aci/llm.py embed()). Embeddings are cached to a local JSON file keyed by a
hash of the source text, so a KB of a few hundred chunks is only ever
embedded once, not recomputed on every process start.

Every hit carries provenance (id, section, regulator, source_url, publication
date, version). The compliance agent is only allowed to cite what this
retriever returns — never model memory. Below `min_score`, or when a
`jurisdictions` filter matches nothing, the caller should treat the result as
"insufficient information" rather than accepting a weak/irrelevant hit.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

from aci import config
from aci.models import RegulatoryHit
from aci.rag.knowledge_base import KB

_WORD = re.compile(r"[a-z0-9\-]+")


def _tokens(s: str) -> list[str]:
    return _WORD.findall(s.lower())


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = math.sqrt(sum(x * x for x in a))
    db = math.sqrt(sum(y * y for y in b))
    return num / (da * db) if da and db else 0.0


class Retriever:
    def __init__(self, kb: list[dict] | None = None, cache_path: Path | None = None):
        self.kb = kb or KB
        self.docs_text = [f"{d['title']} {d['summary']} {d['text']} {' '.join(d['tags'])}" for d in self.kb]
        self.docs = [_tokens(t) for t in self.docs_text]

        # TF-IDF (lexical channel — always available).
        df: Counter = Counter()
        for toks in self.docs:
            for t in set(toks):
                df[t] += 1
        n = len(self.docs)
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1 for t, c in df.items()}
        self.vecs = [self._vec(toks) for toks in self.docs]

        # Dense embeddings (semantic channel — best-effort, cached on disk).
        self.cache_path = cache_path or (config.DATA_DIR / "rag_embeddings_cache.json")
        self._embed_cache: dict[str, list[float]] = self._load_cache()
        self.dense_vecs: list[list[float] | None] = [self._embed_cache.get(_content_hash(t)) for t in self.docs_text]
        # In-process only (queries are request-specific, unlike the KB text
        # above): the compliance agent builds queries from a small, finite set
        # of signal-type combinations, so bulk evaluation over hundreds of
        # transactions reuses the same handful of query strings repeatedly —
        # without this, every search() call would re-embed the query on Ollama.
        self._query_embed_cache: dict[str, list[float] | None] = {}

    def _load_cache(self) -> dict[str, list[float]]:
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps(self._embed_cache))
        except OSError:
            pass

    def ensure_dense_index(self) -> bool:
        """Computes and caches embeddings for any KB entry not already cached.
        Safe to call repeatedly (e.g. at startup) — a no-op once cached, and a
        no-op if Ollama isn't reachable. Returns True if the dense channel is
        usable for at least one document."""
        from aci import llm  # local import avoids a hard dependency at module load

        missing = [(i, t) for i, t in enumerate(self.docs_text) if self.dense_vecs[i] is None]
        if missing:
            vectors = llm.embed([t for _, t in missing])
            if vectors:
                for (i, t), vec in zip(missing, vectors):
                    self.dense_vecs[i] = vec
                    self._embed_cache[_content_hash(t)] = vec
                self._save_cache()
        return any(v is not None for v in self.dense_vecs)

    def _vec(self, toks: list[str]) -> dict[str, float]:
        tf = Counter(toks)
        v = {t: (tf[t] / len(toks)) * self.idf.get(t, 1.0) for t in tf}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return {t: x / norm for t, x in v.items()}

    def _cos_sparse(self, a: dict[str, float], b: dict[str, float]) -> float:
        return sum(a[t] * b.get(t, 0.0) for t in a)

    def search(self, query: str, boost_tags: set[str] | None = None, k: int = 5,
               min_score: float | None = None, jurisdictions: set[str] | None = None) -> list[RegulatoryHit]:
        boost_tags = boost_tags or set()
        candidates = range(len(self.kb))
        if jurisdictions:
            allowed = jurisdictions | {"International"}
            candidates = [i for i in candidates if self.kb[i]["jurisdiction"] in allowed]
            if not candidates:
                return []  # no KB coverage for this corridor — caller must say so, not guess

        qv_sparse = self._vec(_tokens(query))
        query_dense = None
        if any(self.dense_vecs[i] is not None for i in candidates):
            if query not in self._query_embed_cache:
                from aci import llm
                embedded = llm.embed([query])
                self._query_embed_cache[query] = embedded[0] if embedded else None
            query_dense = self._query_embed_cache[query]

        # Sparse TF-IDF cosine is near-zero for genuinely unrelated text (no
        # shared vocabulary), so a low floor works. Dense embedding cosine is
        # NOT near-zero for unrelated text — nomic-embed-text puts even
        # nonsense queries around ~0.25-0.3 against this KB — so once the
        # dense channel is in play the floor must sit above that noise band
        # (empirically ~0.45-0.6 for genuinely relevant hits vs ~0.25-0.3 for
        # nonsense), or "insufficient information" would never fire.
        if min_score is None:
            min_score = 0.35 if query_dense is not None else 0.02

        scored = []
        for i in candidates:
            doc = self.kb[i]
            lexical = self._cos_sparse(qv_sparse, self.vecs[i])
            dense = _cosine(query_dense, self.dense_vecs[i]) if query_dense and self.dense_vecs[i] else None
            # Fuse: dense channel (when available) dominates as it captures
            # semantic similarity beyond shared tokens; lexical always
            # contributes so the system degrades gracefully with no LLM.
            s = (0.4 * lexical + 0.6 * dense) if dense is not None else lexical
            if boost_tags & set(doc["tags"]):
                s += 0.15
            scored.append((s, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        hits = []
        for s, doc in scored[:k]:
            if s < min_score:
                continue
            hits.append(RegulatoryHit(
                id=doc["id"], title=doc["title"], regulator=doc["regulator"],
                jurisdiction=doc["jurisdiction"], section=doc["section"], summary=doc["summary"],
                why="", score=round(s, 3), source_url=doc.get("source_url", ""),
                publication_date=doc.get("publication_date", ""), document_version=doc.get("document_version", ""),
            ))
        return hits
