import sys, time, json, re
from pathlib import Path
from typing import List, Dict, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Field-level F1 ────────────────────────────────────────────────────────────
def compute_field_f1(predicted: dict, ground_truth: dict) -> dict:
    fields = ["source","destination","protocol","port","time_start","time_end","action"]
    results = {}
    for f in fields:
        p = str(predicted.get(f,"")).strip().lower()
        g = str(ground_truth.get(f,"")).strip().lower()
        results[f] = 1.0 if p == g else 0.0
    overall = sum(results.values()) / len(fields)
    results["overall_f1"] = round(overall, 3)
    return results

# ── Hallucination check ───────────────────────────────────────────────────────
def is_hallucinated(command: str, namespace: str) -> bool:
    try:
        from src.document_manager import _col, _embedder
        emb = _embedder.encode(command).tolist()
        res = _col.query(query_embeddings=[emb], n_results=1,
                         where={"namespace": namespace})
        if not res["documents"] or not res["documents"][0]:
            return True
        best_chunk = res["documents"][0][0].lower()
        cmd_words  = set(command.lower().split()) - {"the","a","an","is","in","of","to","and"}
        overlap    = sum(1 for w in cmd_words if w in best_chunk)
        return overlap < 2
    except Exception:
        return False

def hallucination_rate(config: str, namespace: str) -> float:
    lines = [l.strip() for l in config.splitlines() if l.strip() and not l.strip().startswith("!")]
    if not lines:
        return 0.0
    flagged = sum(1 for l in lines if is_hallucinated(l, namespace))
    return round(flagged / len(lines), 3)

# ── Syntax validity (rule-based) ──────────────────────────────────────────────
CISCO_PATTERNS = [
    r"^ip\s+access-list",
    r"^\s*(permit|deny)\s+(tcp|udp|icmp|ip)",
    r"^interface\s+\w",
    r"^ip\s+access-group",
    r"^time-range\s+\w",
    r"^\s*periodic\s+",
    r"^hostname\s+\w",
    r"^enable$",
    r"^configure\s+terminal$",
]
CISCO_RE = [re.compile(p, re.IGNORECASE) for p in CISCO_PATTERNS]

def syntax_validity(config: str) -> float:
    lines = [l.strip() for l in config.splitlines()
             if l.strip() and not l.strip().startswith("!")]
    if not lines:
        return 0.0
    valid = sum(1 for l in lines if any(r.match(l) for r in CISCO_RE))
    return round(valid / len(lines), 3)

# ── Timed pipeline run ────────────────────────────────────────────────────────
def time_pipeline(intent_text: str, model: str, namespaces: List[str],
                  output_format: str = "cisco") -> dict:
    import os
    os.environ["PARSER_MODEL"] = model
    os.environ["GEN_MODEL"]    = model

    from src.config import CHROMA_PATH, TOP_K
    import importlib, src.intent_parser as ip_mod
    import src.config_generator as cg_mod
    import src.safety_validator as sv_mod

    # Reload modules so env vars take effect
    importlib.reload(ip_mod)
    importlib.reload(cg_mod)

    timings = {}

    t0 = time.perf_counter()
    intent_json = ip_mod.parse_intent(intent_text)
    timings["parse_time"] = round(time.perf_counter() - t0, 3)

    t1 = time.perf_counter()
    from src.document_manager import retrieve
    retrieve(intent_text, namespaces)
    timings["rag_time"] = round(time.perf_counter() - t1, 3)

    t2 = time.perf_counter()
    config = cg_mod.generate_config(intent_json, namespaces=namespaces,
                                    output_format=output_format)
    timings["gen_time"] = round(time.perf_counter() - t2, 3)

    t3 = time.perf_counter()
    result = sv_mod.validate(config)
    timings["validate_time"] = round(time.perf_counter() - t3, 3)

    timings["total_time"] = round(
        timings["parse_time"] + timings["rag_time"] +
        timings["gen_time"]   + timings["validate_time"], 3)

    return {
        "model": model,
        "intent": intent_text,
        "intent_json": intent_json,
        "config": config,
        "risk_score": result.score,
        "safe": result.safe,
        "syntax_validity": syntax_validity(config),
        "hallucination_rate": hallucination_rate(config, namespaces[0]) if namespaces else 0.0,
        **timings,
    }

# ── Multi-model comparison ────────────────────────────────────────────────────
def compare_models(intent_text: str, models: List[str],
                   namespaces: List[str]) -> List[dict]:
    results = []
    for model in models:
        try:
            r = time_pipeline(intent_text, model, namespaces)
            results.append(r)
        except Exception as e:
            results.append({"model": model, "error": str(e)})
    return results
