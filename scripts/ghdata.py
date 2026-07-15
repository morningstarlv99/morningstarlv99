"""Reads the account's public shape from the GitHub API.

Standard library only, so the workflow needs no pip install step and the script
stays runnable on any machine with Python 3.

A token is optional. Without one you get anonymous REST (60 requests/hour),
which is enough for everything here except the contribution calendar — that
lives in GraphQL, which requires auth. fetch() reports what it managed to get
so the renderer can degrade honestly instead of inventing numbers.
"""

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone

API = "https://api.github.com"
GRAPHQL = "https://api.github.com/graphql"
UA = "morningstarlv99-profile-art"


def _token():
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def _get(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
    })
    tok = _token()
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _graphql(query, variables):
    tok = _token()
    if not tok:
        return None
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(GRAPHQL, data=body, headers={
        "Authorization": f"Bearer {tok}",
        "Content-Type": "application/json",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    if payload.get("errors"):
        raise RuntimeError(payload["errors"][0].get("message", "graphql error"))
    return payload.get("data")


CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch(user):
    """Return everything the art needs, plus notes on anything unavailable."""
    notes = []
    profile = _get(f"{API}/users/{user}")
    repos = _get(f"{API}/users/{user}/repos?per_page=100&type=owner&sort=pushed")
    repos = [r for r in repos if not r.get("fork") and not r.get("archived")]

    # Drop the profile repo (the one named after the account) from every
    # aggregate. It is the frame, not the picture: counting it would list the
    # profile on the profile, and — because this renderer is far more Python
    # than the journal is C++ — would have the language bar announce a Python
    # developer. The scaffolding must not outvote the work.
    repos = [r for r in repos if r["name"].lower() != user.lower()]

    languages = {}
    commits = 0
    for repo in repos:
        full = repo["full_name"]
        try:
            for lang, byte_count in _get(f"{API}/repos/{full}/languages").items():
                languages[lang] = languages.get(lang, 0) + byte_count
        except urllib.error.HTTPError as exc:
            notes.append(f"languages unavailable for {full} ({exc.code})")
        try:
            # The contributors endpoint counts commits on the default branch,
            # which is the number a reader would recognise as "commits".
            for c in _get(f"{API}/repos/{full}/contributors?per_page=100") or []:
                if c.get("login", "").lower() == user.lower():
                    commits += c.get("contributions", 0)
        except urllib.error.HTTPError as exc:
            # 204/404 here just means the repo has no contributor stats yet.
            if exc.code not in (204, 404):
                notes.append(f"contributors unavailable for {full} ({exc.code})")

    calendar, total_contribs = None, None
    try:
        data = _graphql(CALENDAR_QUERY, {"login": user})
        if data:
            cal = data["user"]["contributionsCollection"]["contributionCalendar"]
            calendar = [[d["contributionCount"] for d in w["contributionDays"]]
                        for w in cal["weeks"]]
            total_contribs = cal["totalContributions"]
        else:
            notes.append("no token: contribution calendar rendered empty")
    except Exception as exc:  # noqa: BLE001 - never fail the render over one panel
        notes.append(f"contribution calendar unavailable ({exc})")

    stars = sum(r.get("stargazers_count", 0) for r in repos)
    total_bytes = sum(languages.values()) or 1
    lang_pct = sorted(
        ((k, v * 100.0 / total_bytes) for k, v in languages.items()),
        key=lambda kv: -kv[1],
    )

    created = profile.get("created_at")
    now = datetime.now(timezone.utc)
    age_days = 0
    if created:
        born = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age_days = max((now - born).days, 0)

    return {
        "user": user,
        "name": profile.get("name") or user,
        "created": created,
        "age_days": age_days,
        "followers": profile.get("followers", 0),
        "repo_count": len(repos),
        "stars": stars,
        "commits": commits,
        "languages": lang_pct,
        "repos": repos,
        "calendar": calendar,
        "total_contributions": total_contribs,
        "generated": datetime.now(timezone.utc),
        "notes": notes,
    }


def ago(iso, now=None):
    """'3 DAYS AGO' style relative time, uppercase for the pixel font."""
    if not iso:
        return "UNKNOWN"
    then = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    delta = (now or datetime.now(timezone.utc)) - then
    days = delta.days
    if days <= 0:
        hours = delta.seconds // 3600
        if hours < 1:
            return "JUST NOW"
        return f"{hours} HOUR{'S' if hours != 1 else ''} AGO"
    if days < 31:
        return f"{days} DAY{'S' if days != 1 else ''} AGO"
    months = days // 30
    if months < 12:
        return f"{months} MONTH{'S' if months != 1 else ''} AGO"
    years = days // 365
    return f"{years} YEAR{'S' if years != 1 else ''} AGO"
