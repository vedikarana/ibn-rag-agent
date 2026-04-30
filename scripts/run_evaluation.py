import sys, json, time, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.intent_parser import parse_intent
from src.config_generator import generate_config
from src.safety_validator import validate
from src.evaluator import compute_field_f1, syntax_validity, hallucination_rate

BENCHMARK_PATH = ROOT / "data" / "intents_benchmark.json"
RESULTS_PATH   = ROOT / "results" / "eval_results.csv"
RESULTS_PATH.parent.mkdir(exist_ok=True)

MODELS     = ["tinyllama", "qwen2.5-coder:0.5b"]
NAMESPACES = ["cisco"]

def run_evaluation(model: str):
    import os
    os.environ["PARSER_MODEL"] = model
    os.environ["GEN_MODEL"]    = model

    if not BENCHMARK_PATH.exists():
        print(f"Benchmark not found at {BENCHMARK_PATH}")
        print("Creating 10-intent starter benchmark...")
        create_starter_benchmark()

    with open(BENCHMARK_PATH) as f:
        benchmark = json.load(f)

    print(f"\n{'='*60}")
    print(f"Model: {model}  |  {len(benchmark)} intents")
    print(f"{'='*60}")

    rows = []
    for i, item in enumerate(benchmark):
        print(f"  [{i+1}/{len(benchmark)}] {item['intent_text'][:55]}...")
        t0 = time.perf_counter()
        try:
            predicted  = parse_intent(item["intent_text"])
            parse_time = round(time.perf_counter() - t0, 3)

            t1 = time.perf_counter()
            config     = generate_config(predicted, namespaces=NAMESPACES, output_format="cisco")
            gen_time   = round(time.perf_counter() - t1, 3)

            t2     = time.perf_counter()
            result = validate(config)
            val_time = round(time.perf_counter() - t2, 3)

            f1      = compute_field_f1(predicted, item.get("ground_truth_json", {}))
            syn_val = syntax_validity(config)
            hall    = hallucination_rate(config, NAMESPACES[0])

            rows.append({
                "model": model, "intent": item["intent_text"],
                "category": item.get("category","general"),
                "difficulty": item.get("difficulty","medium"),
                "overall_f1": f1["overall_f1"],
                "syntax_validity": syn_val,
                "hallucination_rate": hall,
                "risk_score": result.score,
                "parse_time": parse_time,
                "gen_time": gen_time,
                "validate_time": val_time,
                "total_time": round(parse_time + gen_time + val_time, 3),
                "error": "",
            })
            print(f"     F1={f1['overall_f1']:.2f}  Validity={syn_val:.2f}  Time={parse_time+gen_time:.1f}s")
        except Exception as e:
            rows.append({"model":model,"intent":item["intent_text"],"error":str(e)})
            print(f"     ERROR: {e}")

    # Print summary
    valid_rows = [r for r in rows if not r.get("error")]
    if valid_rows:
        avg_f1   = sum(r["overall_f1"] for r in valid_rows) / len(valid_rows)
        avg_syn  = sum(r["syntax_validity"] for r in valid_rows) / len(valid_rows)
        avg_hall = sum(r["hallucination_rate"] for r in valid_rows) / len(valid_rows)
        avg_time = sum(r["total_time"] for r in valid_rows) / len(valid_rows)
        print(f"\nSUMMARY [{model}]")
        print(f"  Intent Extraction F1 : {avg_f1:.3f}")
        print(f"  Syntax Validity      : {avg_syn:.3f}")
        print(f"  Hallucination Rate   : {avg_hall:.3f}")
        print(f"  Avg Total Time (s)   : {avg_time:.2f}")

    return rows

def create_starter_benchmark():
    intents = [
        {"intent_text": "Deny all TCP from 10.0.0.0/8 to 192.168.1.100 port 22",
         "ground_truth_json": {"source":"10.0.0.0/8","destination":"192.168.1.100","protocol":"tcp","port":"22","time_start":"any","time_end":"any","action":"deny"},
         "category":"host-block","difficulty":"easy"},
        {"intent_text": "Permit HTTP from 192.168.10.0/24 to 10.0.1.5 between 09:00 and 18:00",
         "ground_truth_json": {"source":"192.168.10.0/24","destination":"10.0.1.5","protocol":"tcp","port":"80","time_start":"09:00","time_end":"18:00","action":"permit"},
         "category":"time-based","difficulty":"medium"},
        {"intent_text": "Block ICMP from any to 172.16.0.0/16",
         "ground_truth_json": {"source":"any","destination":"172.16.0.0/16","protocol":"icmp","port":"any","time_start":"any","time_end":"any","action":"deny"},
         "category":"protocol-filter","difficulty":"easy"},
        {"intent_text": "Allow DNS from 192.168.0.0/16 to 8.8.8.8 port 53",
         "ground_truth_json": {"source":"192.168.0.0/16","destination":"8.8.8.8","protocol":"udp","port":"53","time_start":"any","time_end":"any","action":"permit"},
         "category":"protocol-filter","difficulty":"easy"},
        {"intent_text": "Deny FTP traffic from 10.0.0.0/8 to any destination",
         "ground_truth_json": {"source":"10.0.0.0/8","destination":"any","protocol":"tcp","port":"21","time_start":"any","time_end":"any","action":"deny"},
         "category":"protocol-filter","difficulty":"easy"},
        {"intent_text": "Block all traffic from 192.168.50.0/24 to 10.0.0.1 after 22:00",
         "ground_truth_json": {"source":"192.168.50.0/24","destination":"10.0.0.1","protocol":"ip","port":"any","time_start":"22:00","time_end":"any","action":"deny"},
         "category":"time-based","difficulty":"medium"},
        {"intent_text": "Permit HTTPS from 172.16.0.0/12 to 10.0.0.50 port 443",
         "ground_truth_json": {"source":"172.16.0.0/12","destination":"10.0.0.50","protocol":"tcp","port":"443","time_start":"any","time_end":"any","action":"permit"},
         "category":"host-block","difficulty":"easy"},
        {"intent_text": "Deny SSH from any source to 192.168.100.0/24 between 21:00 and 06:00",
         "ground_truth_json": {"source":"any","destination":"192.168.100.0/24","protocol":"tcp","port":"22","time_start":"21:00","time_end":"06:00","action":"deny"},
         "category":"time-based","difficulty":"medium"},
        {"intent_text": "Allow UDP from 10.10.0.0/16 to 10.20.0.1 port 161",
         "ground_truth_json": {"source":"10.10.0.0/16","destination":"10.20.0.1","protocol":"udp","port":"161","time_start":"any","time_end":"any","action":"permit"},
         "category":"protocol-filter","difficulty":"easy"},
        {"intent_text": "Block all IP traffic from 192.168.1.50 to 10.0.0.0/8",
         "ground_truth_json": {"source":"192.168.1.50","destination":"10.0.0.0/8","protocol":"ip","port":"any","time_start":"any","time_end":"any","action":"deny"},
         "category":"subnet-block","difficulty":"easy"},
    ]
    BENCHMARK_PATH.parent.mkdir(exist_ok=True)
    with open(BENCHMARK_PATH, "w") as f:
        json.dump(intents, f, indent=2)
    print(f"Created starter benchmark with {len(intents)} intents at {BENCHMARK_PATH}")

if __name__ == "__main__":
    all_rows = []
    for model in MODELS:
        rows = run_evaluation(model)
        all_rows.extend(rows)

    if all_rows:
        keys = [k for k in all_rows[0].keys()]
        with open(RESULTS_PATH, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for r in all_rows:
                w.writerow({k: r.get(k,"") for k in keys})
        print(f"\nResults saved to {RESULTS_PATH}")
