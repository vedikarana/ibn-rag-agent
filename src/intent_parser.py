import sys
import ollama
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import PARSER_MODEL

SYSTEM = """You are a JSON extraction engine. Output ONLY the JSON object. Nothing else.

Return this exact structure:
{"source":"...","destination":"...","protocol":"...","port":"...","time_start":"...","time_end":"...","action":"..."}

Rules:
- Use "any" for unknown values
- action must be "permit" or "deny"
- protocol must be tcp / udp / icmp / ip / any
- NO comments, NO explanation, NO extra text before or after the JSON
"""

FEW_SHOTS = [
    {"role": "user", "content": "Block SSH from Sales VLAN to Finance server"},
    {"role": "assistant", "content": '{"source":"any","destination":"any","protocol":"tcp","port":"22","time_start":"any","time_end":"any","action":"deny"}'},
    {"role": "user", "content": "Allow HTTP from 192.168.1.0/24 to web server 9am to 6pm"},
    {"role": "assistant", "content": '{"source":"192.168.1.0/24","destination":"any","protocol":"tcp","port":"80","time_start":"09:00","time_end":"18:00","action":"permit"}'},
    {"role": "user", "content": "Deny all ICMP from 10.0.0.0/8"},
    {"role": "assistant", "content": '{"source":"10.0.0.0/8","destination":"any","protocol":"icmp","port":"any","time_start":"any","time_end":"any","action":"deny"}'},
]

REQUIRED = {"source", "destination", "protocol", "port", "time_start", "time_end", "action"}


def extract_json(text: str) -> dict | None:
    """Pull the first valid JSON object out of any text, ignoring surrounding prose."""
    # Remove markdown fences
    text = re.sub(r"```json|```", "", text)
    # Remove // comments
    text = re.sub(r"//[^\n]*", "", text)
    # Remove /* */ block comments
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    # Remove trailing commas
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # Find the first { ... } block in the text
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        if REQUIRED.issubset(data.keys()):
            # Replace any [placeholder] values with "any"
            for k, v in data.items():
                if isinstance(v, str) and re.match(r"^\[.*\]$", v.strip()):
                    data[k] = "any"
            return data
    except json.JSONDecodeError:
        pass
    return None


def parse_intent(user_text: str) -> dict:
    messages = (
        [{"role": "system", "content": SYSTEM}]
        + FEW_SHOTS
        + [{"role": "user", "content": user_text}]
    )

    last_raw = ""
    for attempt in range(3):
        resp = ollama.chat(model=PARSER_MODEL, messages=messages)
        raw = resp["message"]["content"].strip()
        last_raw = raw

        result = extract_json(raw)
        if result:
            return result

        # Retry with stricter instruction
        messages.append({"role": "assistant", "content": raw})
        messages.append({
            "role": "user",
            "content": 'Output ONLY the JSON object. Start with { and end with }. No other text.'
        })

    return {"error": "failed to parse intent", "raw": last_raw}