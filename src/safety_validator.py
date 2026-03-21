import re
from dataclasses import dataclass, field
from typing import List

BLOCKLIST = [
    (r"no\s+ip\s+route",          "Removes static routes — can black-hole traffic"),
    (r"erase\s+startup-config",   "Erases startup config — device loses config on reboot"),
    (r"\breload\b",               "Reloads device — causes outage"),
    (r"format\s+flash",           "Formats flash storage — destroys OS"),
    (r"no\s+service\s+password",  "Removes password encryption"),
    (r"delete\s+vlan\.dat",       "Deletes VLAN database"),
    (r"shutdown\s*$",             "Shuts down an interface with no conditions"),
    (r"crypto\s+key\s+zeroize",   "Destroys SSH crypto keys"),
]

CONFLICT_PATTERNS = [
    (r"permit\s+any\s+any",  "Overly permissive — allows all traffic"),
    (r"deny\s+any\s+any\s+log", "May silently drop all traffic if placed early"),
]

@dataclass
class ValidationResult:
    safe:   bool          = True
    score:  int           = 100
    issues: List[str]     = field(default_factory=list)
    warnings: List[str]   = field(default_factory=list)
def validate(config: str) -> ValidationResult:
    result = ValidationResult()
    lines  = config.lower()

    for pattern, reason in BLOCKLIST:
        if re.search(pattern, lines, re.IGNORECASE | re.MULTILINE):
            result.issues.append(f"BLOCKED: {reason}")
            result.score -= 40
            result.safe = False

    for pattern, reason in CONFLICT_PATTERNS:
        if re.search(pattern, lines, re.IGNORECASE):
            result.warnings.append(f"WARNING: {reason}")
            result.score -= 15

    result.score = max(0, result.score)
    if result.score < 50:
        result.safe = False
    return result