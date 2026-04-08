"""Heuristic tokenizer limits for public/embed AI (§24.2) without optional tiktoken dependency."""

from __future__ import annotations


def estimate_llm_tokens(text: str) -> int:
    """
    Conservative rough token count: ~4 chars per token for Latin/Cyrillic mixed text.
    Used only for budget checks before calling an external LLM.
    """
    if not text:
        return 0
    n = len(text.strip())
    return max(1, (n + 3) // 4)
