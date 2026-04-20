from __future__ import annotations

import re
from typing import Tuple


BLOCKED_PATTERNS = {
    r"\bpasswords?\b": "Credential disclosure is out of scope for this assistant.",
    r"\bapi[- ]?keys?\b": "Secret and key handling requests are blocked.",
    r"\bsecrets?\b": "Secret and key handling requests are blocked.",
    r"\bexploit\b": "The assistant does not help with offensive misuse.",
    r"\bmalware\b": "The assistant does not help with offensive misuse.",
    r"\bbypass\b": "Bypass instructions are blocked.",
    r"\bphishing\b": "Social engineering guidance is blocked.",
    r"\bcredential(s)?\b": "Credential disclosure is out of scope for this assistant.",
}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def check_prompt(prompt: str) -> Tuple[bool, str]:
    normalized = prompt.lower()
    for pattern, reason in BLOCKED_PATTERNS.items():
        if re.search(pattern, normalized):
            return False, reason
    return True, ""


def redact_sensitive_info(text: str) -> str:
    redacted = EMAIL_PATTERN.sub("[redacted-email]", text)
    return PHONE_PATTERN.sub("[redacted-phone]", redacted)

