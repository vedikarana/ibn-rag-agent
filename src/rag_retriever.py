from src.config import CHROMA_PATH, TOP_K
from sentence_transformers import SentenceTransformer
import chromadb

_model  = SentenceTransformer("all-MiniLM-L6-v2")
_client = chromadb.PersistentClient(path=CHROMA_PATH)
_col    = _client.get_or_create_collection("network_docs")

def retrieve(query: str, vendor: str) -> str:
    emb     = _model.encode(query).tolist()
    results = _col.query(
        query_embeddings=[emb],
        n_results=TOP_K,
        where={"vendor": vendor}
    )
    chunks = results["documents"][0]
    return "\n---\n".join(chunks)