"""Check Affirm's job board and alert on new non senior engineering roles in Canada.

Runs on GitHub Actions every 3 hours. Uses only the Python standard library.
Opens a GitHub issue (which GitHub emails to you) when new matching jobs appear,
and posts a short daily check-in on days with no new jobs so you know it is running.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FEED_URL = "https://boards-api.greenhouse.io/v1/boards/affirm/jobs"
STATE_FILE = Path(__file__).with_name("seen_jobs.json")
# Daily "still running" check-in time. 15 UTC = 7 AM Vancouver in winter, 8 AM in summer.
HEARTBEAT_HOUR_UTC = 15

# A title must contain one of these to count as engineering.
ENGINEERING_WORDS = re.compile(
    r"\b(engineer|engineering|developer|swe|sde)\b", re.IGNORECASE
)
# Early career titles are always interesting, even without "engineer".
EARLY_CAREER_WORDS = re.compile(
    r"\b(early career|new grad|graduate)\b",
    re.IGNORECASE,
)
# Internships and co-ops are dropped.
INTERNSHIP_WORDS = re.compile(r"\b(intern|interns|internship|co-?op|apprentice\w*)\b", re.IGNORECASE)
# Anything senior is dropped.
SENIOR_WORDS = re.compile(
    r"\b(senior|sr\.?|staff|principal|lead|manager|director|head|vp|"
    r"vice president|architect|distinguished|fellow|iii|iv|v)\b",
    re.IGNORECASE,
)
# Engineering adjacent roles that are not hands on engineering.
NOT_ENGINEERING = re.compile(
    r"\b(program manager|recruit|sales|account|solutions consultant)\w*",
    re.IGNORECASE,
)

CANADA = re.compile(r"\b(canada|toronto|vancouver|montreal|ottawa|calgary|waterloo)\b", re.IGNORECASE)


def fetch_jobs():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "job-alert-bot"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["jobs"]


def is_match(job):
    """Return (matched, note). note explains anything worth flagging."""
    title = job.get("title", "")
    location = (job.get("location") or {}).get("name", "")

    if SENIOR_WORDS.search(title) or NOT_ENGINEERING.search(title) or INTERNSHIP_WORDS.search(title):
        return False, ""
    if not (ENGINEERING_WORDS.search(title) or EARLY_CAREER_WORDS.search(title)):
        return False, ""

    if CANADA.search(location):
        return True, ""
    return False, ""


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None  # first run


def save_state(state):
    state["seen"] = sorted(state["seen"])
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def github_api(path, payload):
    """POST to the GitHub API for this repo. Returns the JSON reply, or None off GitHub."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        print(f"Not running on GitHub Actions, skipping POST {path}.")
        return None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "job-alert-bot",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def mention():
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    return f"\n\n@{owner}" if owner else ""  # the mention makes sure GitHub emails you


def create_issue(title, body):
    """Open a GitHub issue in this repo. GitHub emails the repo owner about it."""
    result = github_api("issues", {"title": title, "body": body + mention()})
    if result:
        print(f"Issue created: {result['html_url']}")
    return result


def send_heartbeat(state, now):
    """Once a day, comment on a single "Bot status" issue so you know it is running."""
    checks = state.get("checks_since_heartbeat", 0)
    body = (
        f"Still running. No new matching jobs since the last update. "
        f"Checked Affirm's job board {checks} time(s) in the last day "
        f"(latest {now.strftime('%Y-%m-%d %H:%M')} UTC)."
    )
    issue = state.get("status_issue")
    if issue:
        result = github_api(f"issues/{issue}/comments", {"body": body + mention()})
    else:
        result = create_issue("Bot status: daily check-in", body)
        if result:
            state["status_issue"] = result["number"]
    print("Heartbeat:", body)


def format_job(job, note):
    location = (job.get("location") or {}).get("name", "")
    line = f"**[{job['title']}]({job['absolute_url']})**  \n{location}"
    if note:
        line += f"  \n_{note}_"
    return line


def main():
    jobs = fetch_jobs()
    print(f"Fetched {len(jobs)} jobs.")
    state = load_state()
    first_run = state is None
    if first_run:
        state = {}
    seen = set(state.get("seen", []))

    new_matches = []
    for job in jobs:
        jid = str(job["id"])
        if jid in seen:
            continue
        seen.add(jid)
        matched, note = is_match(job)
        if matched:
            new_matches.append((job, note))
    state["seen"] = seen

    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    # Touch the file weekly so GitHub keeps the schedule alive (it pauses after 60 idle days).
    last_alive = state.get("last_alive", today)
    if (datetime.fromisoformat(today) - datetime.fromisoformat(last_alive)).days >= 7:
        last_alive = today
    state["last_alive"] = last_alive
    state["checks_since_heartbeat"] = state.get("checks_since_heartbeat", 0) + 1

    if new_matches:
        count = len(new_matches)
        if first_run:
            subject = f"Affirm alert bot is live: {count} matching job(s) open right now"
        else:
            subject = f"{count} new Affirm job(s) for you"
        body = "\n\n".join(format_job(j, n) for j, n in new_matches)
        print(subject)
        print(body)
        create_issue(subject, body)
        state["alerted_since_heartbeat"] = True
    else:
        print("No new matching jobs.")

    # Daily check-in: the first run each day at or after HEARTBEAT_HOUR_UTC.
    # Skipped on days you already got a new job alert, since that proves it is running.
    if now.hour >= HEARTBEAT_HOUR_UTC and state.get("last_heartbeat") != today:
        if not state.get("alerted_since_heartbeat"):
            send_heartbeat(state, now)
        state["last_heartbeat"] = today
        state["checks_since_heartbeat"] = 0
        state["alerted_since_heartbeat"] = False

    save_state(state)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # make failures visible in the Actions log
        print(f"Error: {exc}", file=sys.stderr)
        raise
