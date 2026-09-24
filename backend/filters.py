"""
Very simple word filter (SPEC section 9, point 6).
Blocked words are replaced with *** before a message is forwarded.
Add your own words to BLOCKED_WORDS (lowercase).
"""

import re

BLOCKED_WORDS = [
    "fuck",
    "shit",
    "bitch",
    "asshole",
    "bastard",
    "dick",
    "slut",
    "whore",
]

# \b = word boundary, so "dick" is blocked but "dickens" is not.
_pattern = re.compile(
    r"\b(" + "|".join(re.escape(word) for word in BLOCKED_WORDS) + r")\b",
    re.IGNORECASE,
)


def censor(text: str) -> str:
    return _pattern.sub("***", text)
