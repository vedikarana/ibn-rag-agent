import sys
import re
import ollama
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import GEN_MODEL
from src.document_manager import retrieve

TEMPLATES = {
    "cisco": """You are a Cisco IOS CLI generator. Output ONLY raw CLI commands.
No sentences. No explanation. No backticks. Every line must be a valid Cisco IOS command.

Vendor documentation:
{docs}

Intent: {intent}

Cisco IOS commands (one per line, no explanation):""",

    "juniper": """You are a Juniper JunOS CLI generator. Output ONLY raw JunOS config.
No sentences. No explanation. No backticks.

Vendor documentation:
{docs}

Intent: {intent}

JunOS configuration (no explanation):""",

    "ansible": """You are an Ansible YAML generator. Output ONLY valid YAML starting with ---.
No explanation. No backticks.

Intent: {intent}

Ansible YAML:""",

    "generic": """You are a network CLI generator. Output ONLY raw configuration commands.
No sentences. No explanation. No backticks. Just commands.

Documentation:
{docs}

Intent: {intent}

Commands (no explanation):""",
}

# Lines that start with these words are explanation prose, not CLI commands
PROSE_PATTERNS = [
    r"^(this|these|the|to |in |note|above|below|please|here|follow|make|ensure|you |we |it |as |for |with |all |any |by |if |when|after|before|then|next|now|also|both|each|since|while|where|which|that|there|they|their|your|our)",
    r"^\s*#.*explanation",
    r"^explanation",
    r"^configuration",
    r"^output",
    r"^result",
]
PROSE_RE = re.compile("|".join(PROSE_PATTERNS), re.IGNORECASE)

# Lines that look like real CLI commands start with these
CLI_PATTERNS = re.compile(
    r"^(ip |interface |access-list |router |no |permit |deny |hostname |vlan |"
    r"switchport |spanning|line |service |logging |snmp|crypto|username|aaa|"
    r"set |policy|firewall|filter|term |from |then |---|\s)",
    re.IGNORECASE
)


def clean_output(text: str, output_format: str) -> str:
    """Remove markdown fences and explanation prose, keep only commands."""
    # Strip markdown fences
    text = re.sub(r"```[a-zA-Z]*", "", text)
    text = re.sub(r"```", "", text)

    if output_format == "ansible":
        return text.strip()

    lines = text.splitlines()
    clean = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            clean.append("")
            continue
        # Keep lines that look like CLI commands
        if CLI_PATTERNS.match(stripped):
            clean.append(line.rstrip())
        # Keep short lines that don't look like prose sentences
        elif len(stripped) < 80 and not PROSE_RE.match(stripped) and not stripped.endswith("."):
            clean.append(line.rstrip())

    # Remove leading/trailing blank lines
    result = "\n".join(clean).strip()
    return result if result else text.strip()


def generate_config(
    intent: dict,
    namespaces: List[str],
    output_format: str = "generic",
) -> str:
    query = (
        f"{intent.get('action', 'deny')} "
        f"{intent.get('protocol', 'ip')} "
        f"from {intent.get('source', 'any')} "
        f"to {intent.get('destination', 'any')} "
        f"port {intent.get('port', 'any')}"
    )

    docs = retrieve(query, namespaces=namespaces) if namespaces else ""
    tmpl = TEMPLATES.get(output_format, TEMPLATES["generic"])
    prompt = tmpl.format(
        docs=docs or "No documentation available.",
        intent=str(intent)
    )

    resp = ollama.chat(
        model=GEN_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp["message"]["content"]
    return clean_output(raw, output_format)