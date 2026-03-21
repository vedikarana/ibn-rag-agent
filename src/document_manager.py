import sys
import os
import hashlib
import chromadb
from pathlib import Path
from typing import List
from sentence_transformers import SentenceTransformer
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import CHROMA_PATH, TOP_K

_embedder = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.PersistentClient(path=str(ROOT / CHROMA_PATH.lstrip("./")))
_col = _client.get_or_create_collection("network_docs")


def _load_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(path).pages)
    return open(path, "r", encoding="utf-8", errors="ignore").read()


def ingest_document(file_path: str, namespace: str, chunk_size: int = 500) -> int:
    raw = _load_file(file_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=80
    )
    chunks = [c.strip() for c in splitter.split_text(raw) if len(c.strip()) > 40]
    fhash = hashlib.md5(raw.encode()).hexdigest()[:8]
    ids = [f"{namespace}_{fhash}_{i}" for i in range(len(chunks))]
    embeds = _embedder.encode(chunks, show_progress_bar=False).tolist()
    metas = [{"namespace": namespace, "source": Path(file_path).name} for _ in chunks]

    existing = set(_col.get(where={"namespace": namespace})["ids"])
    new = [
        (i, c, e, m)
        for i, c, e, m in zip(ids, chunks, embeds, metas)
        if i not in existing
    ]

    if new:
        ni, nc, ne, nm = zip(*new)
        _col.add(
            documents=list(nc),
            embeddings=list(ne),
            metadatas=list(nm),
            ids=list(ni)
        )
    return len(new)


def list_namespaces() -> List[str]:
    res = _col.get(include=["metadatas"])
    return sorted({m["namespace"] for m in res["metadatas"] if "namespace" in m})


def get_doc_count(namespace: str) -> int:
    return len(_col.get(where={"namespace": namespace})["ids"])


def delete_namespace(namespace: str):
    ids = _col.get(where={"namespace": namespace})["ids"]
    if ids:
        _col.delete(ids=ids)


def retrieve(query: str, namespaces: List[str], top_k: int = None) -> str:
    k = top_k or TOP_K
    emb = _embedder.encode(query).tolist()

    if "all" in namespaces or not namespaces:
        res = _col.query(
            query_embeddings=[emb],
            n_results=k
        )
    else:
        res = _col.query(
            query_embeddings=[emb],
            n_results=k,
            where={"namespace": {"$in": namespaces}}
        )

    docs = res["documents"][0] if res["documents"] else []
    return "\n---\n".join(docs)