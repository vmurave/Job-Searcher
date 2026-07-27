"""Keyword matching for leadership job titles.

Matches Lead / Head / Teamlead / Руководитель, case-insensitive, with word boundaries
so that words like 'leader-board', 'forehead', 'overhead' don't trigger.
"""
from __future__ import annotations

import re

_PATTERNS = [
    r"\blead(?:s|er|ers|ership)?\b",
    r"\bhead(?:s|ing)?\b",
    r"\bteam[\s\-]?lead\b",
    r"руководител[ьяюеяи]",
    r"начальник",
]
KEYWORD_RE = re.compile("|".join(_PATTERNS), re.IGNORECASE | re.UNICODE)


def is_leadership_title(title: str) -> bool:
    if not title:
        return False
    return bool(KEYWORD_RE.search(title))
