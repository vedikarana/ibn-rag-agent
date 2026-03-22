# IBN-RAG Agent — Intent-Based Networking using RAG + Local LLMs

> Translate natural language network policies into verified, vendor-specific CLI configurations — fully offline, no API cost.

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-teal)](https://fastapi.tiangolo.com)
[![Ollama](https://img.shields.io/badge/LLM-Ollama-green)](https://ollama.ai)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-purple)](https://trychroma.com)
[![LangChain](https://img.shields.io/badge/RAG-LangChain-orange)](https://langchain.com)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## What it does

Network administrators type plain English intents like:

> *"Block all SSH from 10.0.0.0/8 to 192.168.1.100 between 9 PM and 6 AM"*

The system automatically generates:
- Verified **Cisco IOS CLI** commands
- **Juniper JunOS** firewall filters
- **Ansible YAML** playbooks
- A **0–100 risk score** before deployment

All running **100% locally** — no cloud API, no subscription, no data leaves your machine.

---

## Architecture

```
User Intent (Natural Language)
        ↓
Intent Parser — phi3.5 via Ollama
        ↓
Structured JSON {src, dst, proto, port, time, action}
        ↓
RAG Retriever — ChromaDB + MiniLM embeddings
        ↓ (vendor documentation chunks)
Config Generator — qwen2.5-coder via Ollama
        ↓
Safety Validator — blocklist + conflict detection + risk score
        ↓
CLI Output (Cisco / Juniper / Ansible)
```

---

## Quick Start

### 1. Install Ollama and pull models
```bash
# Install Ollama from https://ollama.ai
ollama pull phi3.5
ollama pull qwen2.5-coder:1.5b
```

### 2. Clone and install dependencies
```bash
git clone https://github.com/vedikarana/ibn-rag-agent.git
cd ibn-rag-agent
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run the app
```bash
uvicorn main:app --reload
```

Open http://localhost:8000 in your browser.

### 5. Upload documents and generate configs
1. Upload any vendor PDF or TXT via the UI
2. Give it a tag (e.g. `cisco`, `juniper`, `my_runbook`)
3. Type your network intent
4. Click **Generate Configuration**

---

## Example Intents

| Intent | Output Format |
|--------|--------------|
| `Deny all SSH from 10.0.0.0/8 to 192.168.1.100` | Cisco IOS ACL |
| `Allow HTTP from 192.168.10.0/24 to 10.0.1.5 between 09:00 and 18:00` | Time-based ACL |
| `Block ICMP from any to 172.16.0.0/16` | Juniper firewall filter |
| `Permit DNS from internal hosts to 8.8.8.8 port 53` | Ansible YAML |

---

## Project Structure

```
ibn-rag-agent/
├── src/
│   ├── intent_parser.py       # NL → structured JSON (phi3.5)
│   ├── document_manager.py    # RAG pipeline (ChromaDB)
│   ├── config_generator.py    # JSON → CLI (qwen2.5-coder)
│   ├── safety_validator.py    # Risk scoring + blocklist
│   └── config.py              # Environment settings
├── static/
│   └── index.html             # Web UI
├── scripts/
│   └── ingest_docs.py         # Batch document ingestion
├── data/
│   └── docs/                  # Place vendor PDFs here
├── tests/
│   └── hazard_configs/        # Known-bad configs for validator testing
├── main.py                    # FastAPI entry point
└── requirements.txt
```

---

## Supported Document Types

Upload any of the following to the knowledge base:
- Cisco IOS / IOS-XE configuration guides (PDF)
- Juniper JunOS documentation (PDF)
- Palo Alto PAN-OS guides (PDF)
- NIST security standards (PDF)
- IETF RFCs (PDF)
- Custom CLI cheat sheets (TXT)
- Internal network runbooks (TXT / PDF)

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend API | FastAPI |
| Intent Parser | phi3.5 via Ollama (local) |
| Config Generator | qwen2.5-coder:1.5b via Ollama (local) |
| Vector Database | ChromaDB (persistent, local) |
| Embeddings | all-MiniLM-L6-v2 (sentence-transformers) |
| RAG Framework | LangChain |
| Web UI | HTML + JavaScript (static/index.html) |
| No GPU required | CPU-only, runs on any laptop |

---

## Research Paper

This project accompanies the paper:

**"AI-Driven Intent-Based Networking Agent using Retrieval-Augmented Generation and Local Large Language Models"**

Key contributions:
1. Five-layer IBN-RAG architecture with no cloud dependency
2. Formal intent extraction schema with 80-intent benchmark dataset
3. Safety Validator module with risk scoring and conflict detection
4. Ablation study across phi3, phi3.5, and qwen2.5-coder on CPU hardware

---

## Requirements

- Python 3.10+
- Ollama installed and running
- 4 GB RAM minimum (8 GB recommended)
- No GPU required
- Windows / Mac / Linux

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Vedika Rana**  
GitHub: [@vedikarana](https://github.com/vedikarana)  
Project Link: [github.com/vedikarana/ibn-rag-agent](https://github.com/vedikarana/ibn-rag-agent)
