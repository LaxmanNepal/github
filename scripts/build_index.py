#!/usr/bin/env python3
"""Build a curated public-repository index using GitHub's documented Search API."""
from __future__ import annotations
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "projects.json"
ALLOWLIST = ROOT / "config" / "nepali-creators.json"
CATEGORIES_FILE = ROOT / "config" / "categories.json"
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "LaxmanNepal-GitHub-Explorer"}
if TOKEN:
    HEADERS["Authorization"] = "Bearer " + TOKEN

SEARCH_QUERIES = [
    "stars:>=100 archived:false", "topic:ai stars:>=10 archived:false",
    "topic:machine-learning stars:>=10 archived:false", "topic:llm stars:>=10 archived:false",
    "topic:agent stars:>=5 archived:false", "topic:developer-tools stars:>=10 archived:false",
    "topic:webapp stars:>=10 archived:false", "topic:android stars:>=10 archived:false",
    "topic:ios stars:>=10 archived:false", "topic:fdroid archived:false",
    "topic:foss android archived:false", "topic:privacy android archived:false",
    "topic:android-app archived:false", "topic:open-source-android archived:false",
    "topic:game stars:>=5 archived:false", "topic:games archived:false",
    "topic:windows-app archived:false", "topic:windows desktop-app archived:false",
    "topic:webapp archived:false", "topic:website archived:false", "topic:pwa archived:false",
    "topic:python stars:>=100 archived:false",
    "topic:javascript stars:>=100 archived:false", "topic:typescript stars:>=100 archived:false",
    "topic:rust stars:>=50 archived:false", "topic:go stars:>=50 archived:false",
    "topic:devops stars:>=50 archived:false", "topic:security stars:>=50 archived:false",
    "topic:education stars:>=10 archived:false", "topic:nepal archived:false",
    "topic:nepali archived:false", "nepal in:description archived:false",
]
MAX_PAGES = max(1, min(int(os.getenv("MAX_PAGES_PER_QUERY", "2")), 10))
PER_PAGE = 100

def api(path: str):
    url = API + path
    for attempt in range(5):
        req = urllib.request.Request(url, headers=HEADERS)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code in (403, 429) and (e.headers.get("X-RateLimit-Remaining") == "0" or "rate limit" in body.lower()):
                wait = int(e.headers.get("Retry-After", "60"))
                if attempt < 4:
                    print(f"Rate limited; waiting {min(wait, 300)} seconds", file=sys.stderr)
                    time.sleep(min(wait, 300)); continue
            if e.code >= 500 and attempt < 4:
                time.sleep(2 ** attempt); continue
            raise RuntimeError(f"GitHub API HTTP {e.code}: {body[:400]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 4: raise
            time.sleep(2 ** attempt)
    raise RuntimeError("GitHub API retries exhausted")

def get_release(full_name):
    try:
        data = api(f"/repos/{full_name}/releases/latest")
        return data.get("published_at") or data.get("created_at")
    except Exception:
        return None

def categories_for(repo, category_names):
    text = " ".join([repo.get("name") or "", repo.get("description") or "", " ".join(repo.get("topics") or []), repo.get("language") or ""]).lower()
    topics = set(repo.get("topics") or [])
    result = []
    rules = [
      (0, ["artificial intelligence and machine learning"], ["ai","machine-learning","deep-learning","pytorch","tensorflow","computer-vision","nlp"]),
      (1, ["ai agents and automation"], ["agent","agents","automation","workflow","autonomous-agent"]),
      (2, ["ai models and llm tools"], ["llm","large-language-model","ollama","inference","model","transformer"]),
      (3, ["web applications and saas"], ["webapp","saas","nextjs","react","vue","svelte","web-application"]),
      (4, ["developer tools and ide extensions"], ["developer-tools","vscode","editor","cli","debugger"]),
      (5, ["apis, sdks, libraries, and frameworks"], ["api","sdk","library","libraries","framework","frameworks"]),
      (6, ["mobile applications"], ["android","ios","flutter","react-native","mobile"]),
      (7, ["desktop applications"], ["desktop","electron","tauri","qt"]),
      (8, ["games and game development"], ["game","gamedev","godot","unity","unreal-engine"]),
      (9, ["education and learning"], ["education","learning","tutorial","course","textbook"]),
      (10, ["finance and business"], ["finance","nepse","banking","accounting","business"]),
      (11, ["data science and analytics"], ["data-science","analytics","visualization","pandas","jupyter"]),
      (12, ["cybersecurity and privacy"], ["security","cybersecurity","privacy","encryption","pentesting"]),
      (13, ["productivity and utilities"], ["productivity","utility","utilities","notes","todo"]),
      (14, ["browser extensions"], ["browser-extension","chrome-extension","firefox-addon"]),
      (15, ["self-hosted and devops"], ["self-hosted","docker","kubernetes","devops","homelab"]),
      (16, ["design and creative tools"], ["design","creative","image-editor","video-editor","graphics"]),
      (17, ["websites and website templates"], ["website","portfolio","template","landing-page","blog"]),
    ]
    for idx, _, tags in rules:
        if topics.intersection(tags) or any(term in text for term in tags if len(term) > 4):
            result.append(category_names[idx])
    if repo.get("language") or repo.get("stargazers_count", 0) >= 10:
        result.append(category_names[18])
    return list(dict.fromkeys(result or [category_names[19]]))

def usefulness(repo, release_at, has_readme):
    now = datetime.now(timezone.utc)
    updated = parse_date(repo.get("pushed_at") or repo.get("updated_at"))
    age_days = max(0, (now - updated).days) if updated else 9999
    maintenance = max(0, 30 * (1 - min(age_days, 730) / 730))
    import math
    popularity = min(20, math.log10(max(0, repo.get("stargazers_count", 0)) + 1) * 5)
    community = min(10, math.log10(max(0, repo.get("forks_count", 0)) + 1) * 4)
    docs = 15 if has_readme else 0
    release = 10 if release_at else 0
    demo = 10 if valid_url(repo.get("homepage")) else 0
    return round(min(100, maintenance + popularity + community + docs + release + demo), 1)

def parse_date(s):
    try: return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError): return None

def valid_url(url):
    return isinstance(url, str) and url.startswith("https://") and len(url) < 2000

def main():
    category_names = json.loads(CATEGORIES_FILE.read_text())
    allow = json.loads(ALLOWLIST.read_text())
    creators = {str(x).lower() for x in allow.get("creators", [])}
    explicit_repos = {str(x).lower() for x in allow.get("repositories", [])}
    found = {}
    failures = []
    for query in SEARCH_QUERIES:
        for page in range(1, MAX_PAGES + 1):
            try:
                q = urllib.parse.urlencode({"q": query, "sort": "updated", "order": "desc", "per_page": PER_PAGE, "page": page})
                result = api("/search/repositories?" + q)
                items = result.get("items", [])
                for repo in items:
                    key = (repo.get("full_name") or "").lower()
                    if key and not repo.get("private", False):
                        found[key] = repo
                if len(items) < PER_PAGE or page * PER_PAGE >= min(result.get("total_count", 0), 1000): break
                time.sleep(0.3)
            except Exception as exc:
                failures.append({"query": query, "page": page, "error": str(exc)})
                print(f"Search failed for {query!r} page {page}: {exc}", file=sys.stderr)
                break
    if not found:
        print("No repositories retrieved; refusing to overwrite last known-good dataset.", file=sys.stderr)
        sys.exit(1)
    old = {}
    if DATA.exists():
        try: old = json.loads(DATA.read_text())
        except Exception: pass
    old_by_name = {p.get("full_name","").lower():p for p in old.get("projects", [])}
    projects = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    for key, repo in found.items():
        owner = repo.get("owner") or {}
        topics = repo.get("topics") or []
        homepage = repo.get("homepage")
        # Only known allowlisted creator/repository entries establish creator evidence.
        creator_verified = owner.get("login", "").lower() in creators or key in explicit_repos
        nepal_terms = set(t.lower() for t in topics).intersection({"nepal","nepali","nepalese"})
        description = (repo.get("description") or "").lower()
        nepal_related = creator_verified or key in explicit_repos or bool(nepal_terms) or ("nepal" in description and bool(set(topics).intersection({"nepal","nepali","nepalese","nepse"})))
        previous = old_by_name.get(key, {})
        # Search API does not include README/release on every request; preserve prior known release and doc signals.
        release_at = previous.get("latest_release_at")
        has_readme = previous.get("has_readme", False)
        p = {
          "id": repo.get("id"), "full_name": repo.get("full_name"), "name": repo.get("name"),
          "owner_login": owner.get("login"), "owner_avatar_url": owner.get("avatar_url"),
          "owner_profile_url": owner.get("html_url") or owner.get("url"),
          "repository_url": repo.get("html_url"), "description": repo.get("description"),
          "homepage_url": homepage if valid_url(homepage) else None, "language": repo.get("language"),
          "topics": topics, "categories": categories_for(repo, category_names),
          "license_spdx_id": ((repo.get("license") or {}).get("spdx_id") if isinstance(repo.get("license"), dict) else None),
          "is_open_source": bool((repo.get("license") or {}).get("spdx_id") and (repo.get("license") or {}).get("spdx_id") not in ("NOASSERTION", "NONE")),
          "stargazers_count": repo.get("stargazers_count"), "forks_count": repo.get("forks_count"),
          "open_issues_count": repo.get("open_issues_count"), "created_at": repo.get("created_at"),
          "updated_at": repo.get("updated_at"), "pushed_at": repo.get("pushed_at"),
          "latest_release_at": release_at, "has_release": bool(release_at),
          "has_readme": has_readme, "is_archived": bool(repo.get("archived")),
          "is_fork": bool(repo.get("fork")), "has_demo": valid_url(homepage),
          "demo_url": homepage if valid_url(homepage) else None,
          "is_android_app": bool(set(t.lower() for t in topics).intersection({"android","apk","android-app","mobile-app","fdroid","android-game","mobile-game"}) or re.search(r"\b(android|apk|fdroid|f-droid)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)),
          "is_game": bool(set(t.lower() for t in topics).intersection({"game","games","gamedev","android-game","mobile-game","godot","unity","unreal-engine"}) or re.search(r"\b(game|games|gaming)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)),
          "is_web_app": bool(set(t.lower() for t in topics).intersection({"webapp","web-app","website","web","pwa","saas","self-hosted-web"}) or re.search(r"\b(web app|web application|website|web-based|progressive web app|pwa|saas)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)),
          "is_windows_app": bool(set(t.lower() for t in topics).intersection({"windows","windows-app","winui","winforms","wpf","msix"}) or re.search(r"\b(windows app|windows desktop|winui|winforms|wpf|msix)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)),
          "apk_download_url": (repo.get("html_url") or "") + "/releases" if (set(t.lower() for t in topics).intersection({"android","apk","android-app","mobile-app"}) or re.search(r"\b(android|apk)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)) else None,
          "windows_download_url": (repo.get("html_url") or "") + "/releases" if (set(t.lower() for t in topics).intersection({"windows","windows-app","winui","winforms","wpf","msix"}) or re.search(r"\b(windows app|windows desktop|winui|winforms|wpf|msix)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)) else None,
          "is_hidden_app": bool((set(t.lower() for t in topics).intersection({"fdroid","f-droid","foss","privacy","open-source-android","android-app"}) or re.search(r"\b(fdroid|f-droid|foss|open.source android|privacy app)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I)) and ((repo.get("license") or {}).get("spdx_id") not in (None, "", "NOASSERTION", "NONE")) and (set(t.lower() for t in topics).intersection({"android","apk","android-app","mobile-app","fdroid","f-droid","android-game","mobile-game"}) or re.search(r"\b(android|apk|fdroid|f-droid)\b", " ".join([repo.get("name") or "", repo.get("description") or ""]), re.I))),
          "usefulness_score": usefulness(repo, release_at, has_readme),
          "nepal_related": bool(nepal_related), "nepali_creator_verified": bool(creator_verified),
          "nepali_creator_evidence": "Allowlisted public creator/repository" if creator_verified else ("Project metadata/topics indicate Nepal-related purpose; creator identity not verified" if nepal_related else None),
          "last_indexed_at": now,
        }
        projects.append(p)
    projects.sort(key=lambda p: (p.get("updated_at") or ""), reverse=True)
    nepals = sum(1 for p in projects if p["nepal_related"])
    payload = {"schema_version": 1, "generated_at": now, "source": "GitHub REST Search API; curated queries with Search API limits", "query_count": len(SEARCH_QUERIES), "total": len(projects), "nepal_total": nepals, "failures": failures, "projects": projects}
    tmp = DATA.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
    check = json.loads(tmp.read_text())
    ids, names = set(), set()
    for p in check["projects"]:
        if not p.get("id") or not p.get("full_name") or not isinstance(p.get("stargazers_count"), int):
            raise ValueError(f"Invalid required repository fields: {p.get('full_name')}")
        if p["id"] in ids or p["full_name"].lower() in names: raise ValueError("Duplicate repository id/name")
        ids.add(p["id"]); names.add(p["full_name"].lower())
        for field in ("updated_at","created_at","pushed_at"):
            if p.get(field) and not parse_date(p[field]): raise ValueError(f"Invalid {field} on {p['full_name']}")
        if p.get("demo_url") and not valid_url(p["demo_url"]): raise ValueError("Invalid demo URL")
    tmp.replace(DATA)
    report = {"generated_at": now, "repositories": len(projects), "nepal_related": nepals, "search_queries": len(SEARCH_QUERIES), "search_failures": failures}
    (ROOT / "data" / "index-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
if __name__ == "__main__": main()
