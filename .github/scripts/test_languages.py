# Run: python3 .github/scripts/test_languages.py
from collections import Counter

from languages import fmt, render

shares = {
    "zanellig": Counter(TypeScript=770, Python=110, Java=36, Rust=33, JavaScript=26, Shell=20, Go=5),
    "cogniarg": Counter(TypeScript=680, Python=280, JavaScript=22, Shell=11, PLpgSQL=8, Rust=3),
}
svg = render("dark", shares)
body = svg.split("</title>")[1]

assert fmt(0) == "–" and fmt(0.0005) == "<0.1%" and fmt(0.036) == "3.6%" and fmt(0.77) == "77%"
assert body.count(">TypeScript<") == 1 and body.count(">Python<") == 1  # column headers, not repeated per row
assert body.count(">Java<") == 1  # only in the personal row: each source lists its own languages
assert ">Go<" not in body  # personal "Also" stops at four
assert ">–<" not in body  # nobody shows a language they don't use
print("ok")
