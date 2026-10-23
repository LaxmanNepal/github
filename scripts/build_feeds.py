#!/usr/bin/env python3
"""Generate a small RSS feed and append-only aggregate index history."""
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://laxmannepal.com.np/github/"
data = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
report_path = ROOT / "data/index-report.json"
report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
generated = data.get("generated_at") or report.get("generated_at") or datetime.now(timezone.utc).isoformat()
projects = data.get("projects", [])
history_path = ROOT / "data/history.json"
history = {"schema_version": 1, "snapshots": []}
if history_path.exists():
    try:
        old = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(old.get("snapshots"), list):
            history["snapshots"] = old["snapshots"]
    except (ValueError, OSError):
        pass
snapshot = {
    "generated_at": generated,
    "repositories": len(projects),
    "nepal_related": sum(1 for p in projects if p.get("nepal_related")),
    "archived": sum(1 for p in projects if p.get("is_archived")),
    "with_license": sum(1 for p in projects if p.get("license_spdx_id")),
    "with_homepage": sum(1 for p in projects if p.get("homepage_url")),
    "search_queries": report.get("search_queries", data.get("query_count", 0)),
    "search_failures": len(report.get("search_failures", data.get("failures", []))),
}
snapshots = [x for x in history["snapshots"] if x.get("generated_at") != generated]
snapshots.append(snapshot)
snapshots.sort(key=lambda x: x.get("generated_at", ""))
history["snapshots"] = snapshots[-365:]
(ROOT / "data/history.json").write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")

def atom_date(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        return datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

items = sorted(projects, key=lambda p: (p.get("updated_at") or "", p.get("stargazers_count") or 0), reverse=True)[:50]
xml = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0"><channel>',
       '<title>GitHub Explorer — Recently updated projects</title>',
       f'<link>{BASE}</link>',
       '<description>Recently updated repositories in the curated GitHub Explorer index.</description>',
       '<language>en</language>', f'<lastBuildDate>{atom_date(generated)}</lastBuildDate>']
for p in items:
    name = p.get("full_name") or p.get("name") or "GitHub repository"
    link = p.get("repository_url") or "https://github.com/" + name
    desc = (p.get("description") or "No repository description provided.")[:500]
    pub = p.get("updated_at") or generated
    xml.extend(["<item>", f"<title>{escape(name)}</title>", f"<link>{escape(link)}</link>",
                f"<guid isPermaLink=\"false\">{escape(name)}</guid>", f"<description>{escape(desc)}</description>",
                f"<pubDate>{atom_date(pub)}</pubDate>", "</item>"])
xml.extend(["</channel></rss>", ""])
(ROOT / "feed.xml").write_text("\n".join(xml), encoding="utf-8")
print(f"Generated feed.xml ({len(items)} items) and data/history.json ({len(history['snapshots'])} snapshots)")
