from dotenv import load_dotenv
import os
load_dotenv()
PARSER_MODEL = os.getenv("PARSER_MODEL", "phi3.5")
GEN_MODEL    = os.getenv("GEN_MODEL", "qwen2.5-coder:1.5b")
CHROMA_PATH  = os.getenv("CHROMA_PATH", "./data/chroma_db")
TOP_K        = int(os.getenv("TOP_K_CHUNKS", 5))