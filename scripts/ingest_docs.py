import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.config import CHROMA_PATH
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb

def ingest(pdf_path: str, vendor: str):
    print(f"Loading {pdf_path}...")
    loader = PyPDFLoader(pdf_path)
    docs   = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=80)
    chunks = splitter.split_documents(docs)
    print(f"  {len(chunks)} chunks created")

    model  = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    col    = client.get_or_create_collection("network_docs")

    texts = [c.page_content for c in chunks]
    embeds = model.encode(texts, show_progress_bar=True).tolist()
    ids    = [f"{vendor}_{i}" for i in range(len(texts))]
    metas  = [{"vendor": vendor} for _ in texts]

    col.add(documents=texts, embeddings=embeds, metadatas=metas, ids=ids)
    print(f"  Stored {len(texts)} chunks for vendor='{vendor}'")

if __name__ == "__main__":
    ingest("data/docs/cisco_acl.pdf",       "cisco")
    ingest("data/docs/juniper_firewall.pdf", "juniper")
    print("Done. ChromaDB ready.")