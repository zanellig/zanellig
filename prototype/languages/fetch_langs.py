# PROTOTYPE, throwaway. Snapshots language bytes + zanellig's share per repo into data.js.
# Run: python3 prototype/languages/fetch_langs.py
import json, subprocess, time, pathlib
from concurrent.futures import ThreadPoolExecutor

USER, ORG = "zanellig", "cogniarg"

def gh(path, tries=1):
    for _ in range(tries):
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() not in ("", "{}"):
            return json.loads(r.stdout)
        time.sleep(3)  # stats endpoints answer 202 + {} while GitHub computes them
    return None

def repos(owner):
    out = subprocess.run(["gh", "repo", "list", owner, "--limit", "300", "--json", "name,isFork,isPrivate,isArchived,pushedAt"],
                         capture_output=True, text=True, check=True).stdout
    return [r for r in json.loads(out) if not r["isFork"]]

YEAR_AGO = time.time() - 365 * 86400

def share(owner, name):
    # ponytail: additions from stats/contributors; deletions, renames and lockfile churn not filtered
    stats = gh(f"repos/{owner}/{name}/stats/contributors", tries=10) or []
    adds = {s["author"]["login"] if s.get("author") else None: sum(w["a"] for w in s["weeks"]) for s in stats}
    mine = next((s for s in stats if s.get("author") and s["author"]["login"] == USER), None)
    recent = sum(w["a"] for w in mine["weeks"] if w["w"] >= YEAR_AGO) if mine else 0
    total = sum(adds.values())
    return ((adds.get(USER, 0) / total) if total else 0.0), recent

def row(owner, r):
    name = r["name"]
    sh, recent = share(owner, name)
    return {"owner": owner, "name": name, "private": r["isPrivate"], "archived": r["isArchived"],
            "pushedAt": r["pushedAt"], "langs": gh(f"repos/{owner}/{name}/languages") or {},
            "share": sh, "recentAdds": recent}

jobs = [(USER, r) for r in repos(USER)] + [(ORG, r) for r in repos(ORG)]
with ThreadPoolExecutor(8) as ex:
    rows = list(ex.map(lambda j: row(*j), jobs))
rows = [r for r in rows if r["owner"] == USER or r["share"] > 0]  # org repos only if I contributed

out = pathlib.Path(__file__).with_name("data.js")
out.write_text("window.REPOS = " + json.dumps(rows, indent=1) + ";\n")
print(f"{len(rows)} repos -> {out}")
