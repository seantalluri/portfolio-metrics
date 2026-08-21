#!/usr/bin/env python3
"""Publish aggregate-only activity metrics from one private repo.

Security model:
- GITHUB_TOKEN reads only the current private repository.
- PORTFOLIO_PUBLISH_TOKEN can write only to the public portfolio-metrics repo.
- No commit messages, SHAs, branches, authors, filenames, issue titles, or diffs are published.
"""

import base64
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com"
SOURCE_REPO = os.environ["GITHUB_REPOSITORY"]
SOURCE_TOKEN = os.environ.get("GITHUB_TOKEN", "")
PUBLISH_TOKEN = os.environ.get("PORTFOLIO_PUBLISH_TOKEN", "")
METRICS_REPO = os.environ.get("PORTFOLIO_METRICS_REPO", "seantalluri/portfolio-metrics")
SLUG = os.environ["PORTFOLIO_SLUG"]
LABEL = os.environ["PORTFOLIO_LABEL"]


def request_json(path, token, method="GET", body=None, params=None):
    url = API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "portfolio-metrics-publisher",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return (json.loads(raw) if raw else None), resp.headers


def count_all(endpoint, token, params=None):
    params = dict(params or {})
    params["per_page"] = 100
    page = 1
    total = 0
    while True:
        params["page"] = page
        rows, _ = request_json(endpoint, token, params=params)
        total += len(rows)
        if len(rows) < 100:
            return total
        page += 1


def count_recent_commits(default_branch, cutoff_iso):
    return count_all(
        f"/repos/{SOURCE_REPO}/commits",
        SOURCE_TOKEN,
        {"sha": default_branch, "since": cutoff_iso},
    )


def count_recent_prs(cutoff):
    page = 1
    total = 0
    while True:
        rows, _ = request_json(
            f"/repos/{SOURCE_REPO}/pulls",
            SOURCE_TOKEN,
            params={
                "state": "all",
                "sort": "created",
                "direction": "desc",
                "per_page": 100,
                "page": page,
            },
        )
        if not rows:
            return total
        stop = False
        for pr in rows:
            created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
            if created >= cutoff:
                total += 1
            else:
                stop = True
                break
        if stop or len(rows) < 100:
            return total
        page += 1


def current_file_sha(path):
    try:
        obj, _ = request_json(f"/repos/{METRICS_REPO}/contents/{path}", PUBLISH_TOKEN)
        return obj.get("sha")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def publish(path, content, message):
    body = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": "main",
    }
    sha = current_file_sha(path)
    if sha:
        body["sha"] = sha
    request_json(f"/repos/{METRICS_REPO}/contents/{path}", PUBLISH_TOKEN, method="PUT", body=body)


def fmt(n):
    return f"{n:,}"


def make_svg(total_commits, total_prs, recent_commits, recent_prs, updated):
    label = html.escape(LABEL)
    accessible = html.escape(
        f"{LABEL}: lifetime {total_commits} commits and {total_prs} PRs; "
        f"last 30 days {recent_commits} commits and {recent_prs} PRs"
    )
    line2 = (
        f"Lifetime  {fmt(total_commits)} commits · {fmt(total_prs)} PRs"
        f"     |     Last 30d  {fmt(recent_commits)} commits · {fmt(recent_prs)} PRs"
    )
    line2 = html.escape(line2)
    updated_text = html.escape(updated.strftime("Updated %Y-%m-%d UTC"))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="58" role="img" aria-label="{accessible}">
  <rect width="720" height="58" rx="8" fill="#24292f"/>
  <text x="14" y="21" fill="#ffffff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="13" font-weight="700">{label}</text>
  <text x="706" y="21" text-anchor="end" fill="#7ee787" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" font-weight="700">PRIVATE ENGINEERING</text>
  <text x="14" y="43" fill="#c9d1d9" font-family="Verdana,DejaVu Sans,sans-serif" font-size="12">{line2}</text>
  <text x="706" y="43" text-anchor="end" fill="#8b949e" font-family="Verdana,DejaVu Sans,sans-serif" font-size="9">{updated_text}</text>
</svg>'''


def main():
    if not SOURCE_TOKEN:
        print("::error::GITHUB_TOKEN is unavailable")
        return 2
    if not PUBLISH_TOKEN:
        print("::notice::PORTFOLIO_PUBLISH_TOKEN is not configured; metrics publish skipped")
        return 0

    repo, _ = request_json(f"/repos/{SOURCE_REPO}", SOURCE_TOKEN)
    default_branch = repo["default_branch"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    cutoff_iso = cutoff.isoformat().replace("+00:00", "Z")

    total_commits = count_all(
        f"/repos/{SOURCE_REPO}/commits", SOURCE_TOKEN, {"sha": default_branch}
    )
    total_prs = count_all(
        f"/repos/{SOURCE_REPO}/pulls",
        SOURCE_TOKEN,
        {"state": "all", "sort": "created", "direction": "desc"},
    )
    recent_commits = count_recent_commits(default_branch, cutoff_iso)
    recent_prs = count_recent_prs(cutoff)

    payload = {
        "label": LABEL,
        "visibility": "private",
        "window_days": 30,
        "lifetime": {"commits": total_commits, "pull_requests": total_prs},
        "last_30_days": {"commits": recent_commits, "pull_requests": recent_prs},
        "updated_at": now.isoformat().replace("+00:00", "Z"),
    }

    publish(
        f"metrics/{SLUG}.json",
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        f"chore(metrics): refresh {SLUG} data",
    )
    publish(
        f"metrics/{SLUG}.svg",
        make_svg(total_commits, total_prs, recent_commits, recent_prs, now),
        f"chore(metrics): refresh {SLUG} badge",
    )

    print(
        f"Published {LABEL}: lifetime {total_commits} commits/{total_prs} PRs; "
        f"30d {recent_commits} commits/{recent_prs} PRs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
