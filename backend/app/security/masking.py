import re


SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"), "[EMAIL_MASKED]"),
    (re.compile(r"\b\d{6}[-\s]?[1-4]\d{6}\b"), "[RRN_MASKED]"),
    (re.compile(r"\b\d{3}[-\s]?\d{2}[-\s]?\d{5}\b"), "[BIZ_NO_MASKED]"),
    (re.compile(r"\b\d{2,6}[-\s]?\d{2,6}[-\s]?\d{5,8}(?:[-\s]?\d{1,4})?\b"), "[ACCOUNT_MASKED]"),
    (re.compile(r"\b01[016789][-\s.]?\d{3,4}[-\s.]?\d{4}\b"), "[PHONE_MASKED]"),
    (re.compile(r"\b(?:0\d{1,2}[-\s.]?)?\d{3,4}[-\s.]?\d{4}\b"), "[PHONE_MASKED]"),
)


def mask_sensitive_text(text: str | None) -> str:
    if not text:
        return ""

    masked = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        masked = pattern.sub(replacement, masked)
    return masked
