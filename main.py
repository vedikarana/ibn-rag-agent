import sys, os, tempfile, json
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from src.intent_parser import parse_intent
from src.config_generator import generate_config
from src.safety_validator import validate
from src.document_manager import (
    ingest_document, list_namespaces, get_doc_count, delete_namespace
)

app = FastAPI(title="IBN-RAG API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index(): return FileResponse("static/index.html")

@app.get("/api/namespaces")
def get_namespaces():
    ns = list_namespaces()
    return {"namespaces": [{"name": n, "chunks": get_doc_count(n)} for n in ns]}

@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...), namespace: str = Form(...)):
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read()); tmp_path = tmp.name
    try:
        count = ingest_document(tmp_path, namespace=namespace.strip())
    finally:
        os.unlink(tmp_path)
    return {"chunks": count, "namespace": namespace}

@app.delete("/api/namespaces/{name}")
def delete_ns(name: str):
    delete_namespace(name); return {"deleted": name}

class GenerateRequest(BaseModel):
    intent: str
    namespaces: List[str]
    output_format: str = "generic"

@app.post("/api/generate")
def generate(req: GenerateRequest):
    intent_json = parse_intent(req.intent)
    if "error" in intent_json:
        raise HTTPException(status_code=422, detail=intent_json)
    config = generate_config(intent_json, namespaces=req.namespaces, output_format=req.output_format)
    result = validate(config)
    return {
        "intent_json": intent_json,
        "config": config,
        "safe": result.safe,
        "score": result.score,
        "issues": result.issues,
        "warnings": result.warnings,
    }