#!/usr/bin/env python3
"""Render assets/languages-{dark,light}.svg.

For my own repos and for the cogniarg repos I contribute to: the lines I added in the
last 12 months, split by each repo's language mix. Markup (HTML, CSS, ...) is left out.

Locally it uses your `gh` login. In CI, ZANELLIG_TOKEN and COGNIARG_TOKEN must be
read-only tokens for each owner (fine-grained tokens are limited to one owner).
"""
import json
import os
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from xml.sax.saxutils import escape

USER = "zanellig"
SOURCES = [(USER, "Personal repos"), ("cogniarg", "cogniarg")]
MARKUP = {"HTML", "CSS", "SCSS", "Sass", "Less", "Stylus", "MDX", "Jupyter Notebook"}
ASSETS = Path(__file__).resolve().parents[2] / "assets"
FONT = "-apple-system,BlinkMacSystemFont,Segoe UI,Noto Sans,Helvetica,Arial,sans-serif"
# Same palette as the stack gallery (assets/README.md)
THEMES = {
    "dark": {"ink": "#c9d1d9", "strong": "#d1d9e0", "muted": "#8b949e", "rule": "#21262d"},
    "light": {"ink": "#24292f", "strong": "#24292f", "muted": "#57606a", "rule": "#eaeef2"},
}


def gh(owner, *args):
    token = os.environ.get(f"{owner.upper()}_TOKEN")
    env = {**os.environ, "GH_TOKEN": token} if token else None
    return subprocess.run(["gh", *args], stdout=subprocess.PIPE, text=True, check=True, env=env).stdout


def repos(owner):
    names = [r["name"] for r in json.loads(gh(owner, "repo", "list", owner, "--source", "--limit", "1000", "--json", "name"))]
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for name in names:  # Actions logs are public; keep private repo names out of errors and tracebacks
            print(f"::add-mask::{name}", flush=True)
    return names


def recent_additions(owner, repo):
    for _ in range(12):
        out = gh(owner, "api", f"repos/{owner}/{repo}/stats/contributors")
        if out.strip() != "{}":  # 202 + {} while GitHub computes the stats; 204 + nothing for empty repos
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"GitHub never finished computing stats for {owner}/{repo}")
    since = time.time() - 365 * 86400
    for c in json.loads(out or "[]"):
        if c["author"] and c["author"]["login"] == USER:
            return sum(w["a"] for w in c["weeks"] if w["w"] >= since)
    return 0


def repo_lines(owner, repo):
    adds = recent_additions(owner, repo)
    if not adds:
        return Counter()
    langs = {k: v for k, v in json.loads(gh(owner, "api", f"repos/{owner}/{repo}/languages")).items() if k not in MARKUP}
    total = sum(langs.values())
    return Counter({k: adds * v / total for k, v in langs.items()}) if total else Counter()


def lines_by_language(owner):
    lines = Counter()
    with ThreadPoolExecutor(8) as pool:
        for c in pool.map(lambda repo: repo_lines(owner, repo), repos(owner)):
            lines.update(c)
    return lines


def fmt(p):
    if not p:
        return "–"
    return f"{p * 100:.0f}%" if p >= 0.1 else f"{p * 100:.1f}%" if p >= 0.001 else "<0.1%"


def fmt_lines(n):
    return f"{n / 1e6:.1f}M lines" if n >= 1e6 else f"{n / 1e3:.0f}k lines" if n >= 1e3 else f"{n:.0f} lines"


def text(x, y, s, fill, size, weight=400, anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(s)}</text>')


def render(theme, shares):
    """Grid: one row per source; the two top languages overall as columns, then each source's own next four."""
    t = THEMES[theme]
    cols = [lang for lang, _ in sum(shares.values(), Counter()).most_common(2)]
    body = [text(116, 12, cols[0], t["muted"], 11), text(210, 12, cols[1], t["muted"], 11), text(300, 12, "Also", t["muted"], 11)]
    title = []
    for i, (owner, name) in enumerate(SOURCES):
        lines = shares[owner]
        total = sum(lines.values())
        top = 24 + i * 88
        body += [
            text(0, top + 30, name, t["ink"], 13, 600),
            text(0, top + 48, fmt_lines(total), t["muted"], 11),
            text(116, top + 46, fmt(lines[cols[0]] / total), t["strong"], 32, 600),
            text(210, top + 46, fmt(lines[cols[1]] / total), t["muted"], 32, 600),
        ]
        also = [(lang, n) for lang, n in lines.most_common() if lang not in cols][:4]
        for j, (lang, n) in enumerate(also):
            y = top + 14 + j * 16
            body += [text(300, y, lang, t["muted"], 11), text(400, y, fmt(n / total), t["muted"], 11, anchor="end")]
        title.append(f"{name}: " + ", ".join(f"{lang} {fmt(n / total)}" for lang, n in lines.most_common(6)))
    body.append(f'<line x1="0" y1="102" x2="400" y2="102" stroke="{t["rule"]}" stroke-width="1"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="192" viewBox="0 0 400 192" role="img">\n'
            f'  <title>{escape(". ".join(title))}</title>\n  ' + "\n  ".join(body) + "\n</svg>\n")


def main():
    shares = {owner: lines_by_language(owner) for owner, _ in SOURCES}
    for owner, lines in shares.items():
        if not lines:  # usually a missing or under-scoped token; keep last week's images instead
            sys.exit(f"No lines found for {owner}")
    for theme in THEMES:
        (ASSETS / f"languages-{theme}.svg").write_text(render(theme, shares))


if __name__ == "__main__":
    main()
