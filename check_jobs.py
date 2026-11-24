"""Check Affirm's job board and alert on new non senior engineering roles.

Runs on GitHub Actions every 3 hours. Uses only the Python standard library.
Opens a GitHub issue (which GitHub emails to you) only when new matching jobs appear.
"""

import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FEED_URL = "https://boards-api.greenhouse.io/v1/boards/affirm/jobs?content=true"
STATE_FILE = Path(__file__).with_name("seen_jobs.json")

# A title must contain one of these to count as engineering.
ENGINEERING_WORDS = re.compile(
    r"\b(engineer|engineering|developer|swe|sde)\b", re.IGNORECASE
)
# Early career titles are always interesting, even without "engineer".
EARLY_CAREER_WORDS = re.compile(
    r"\b(early career|new grad|graduate|intern|internship|co-?op|apprentice)\b",
    re.IGNORECASE,
)
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
USA = re.compile(r"\b(united states|usa|us|u\.s\.|remote us|new york|san francisco|chicago|seattle|pittsburgh)\b", re.IGNORECASE)
# Phrases in a US posting that suggest a Canadian could not get hired.
NO_SPONSOR = re.compile(
    r"(not (be )?(able to )?(offer|provide) (visa )?sponsorship|"
    r"(will|does|do) not sponsor|without (the need for )?(current or future )?(visa )?sponsorship|"
    r"must be (legally )?authorized to work in the (u\.s\.|us|united states)|"
    r"us citizen|u\.s\. citizen|security clearance)",
    re.IGNORECASE,
)


def fetch_jobs():
    req = urllib.request.Request(FEED_URL, headers={"User-Agent": "job-alert-bot"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)["jobs"]


def is_match(job):
    """Return (matched, note). note explains anything worth flagging."""
    title = job.get("title", "")
    location = (job.get("location") or {}).get("name", "")

    if SENIOR_WORDS.search(title) or NOT_ENGINEERING.search(title):
        return False, ""
    if not (ENGINEERING_WORDS.search(title) or EARLY_CAREER_WORDS.search(title)):
        return False, ""

    if CANADA.search(location):
        return True, ""
    if USA.search(location):
        text = html.unescape(job.get("content", ""))
        if NO_SPONSOR.search(text):
            return True, "US role, posting mentions US work authorization or no sponsorship. Check before applying."
        return True, "US role, no sponsorship limits mentioned in the posting."
    return False, ""


def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return None  # first run


def save_state(seen_ids, last_alive):
    STATE_FILE.write_text(
        json.dumps({"seen": sorted(seen_ids), "last_alive": last_alive}, indent=2) + "\n"
    )


def create_issue(title, body):
    """Open a GitHub issue in this repo. GitHub emails the repo owner about it."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER")
    if not (token and repo):
        print("Not running on GitHub Actions, skipping issue.")
        return
    if owner:
        body += f"\n\n@{owner}"  # the mention makes sure GitHub notifies you
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title, "body": body}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "job-alert-bot",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print(f"Issue created: {json.load(resp)['html_url']}")


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
    seen = set(state["seen"]) if state else set()

    new_matches = []
    for job in jobs:
        jid = str(job["id"])
        if jid in seen:
            continue
        seen.add(jid)
        matched, note = is_match(job)
        if matched:
            new_matches.append((job, note))

    today = datetime.now(timezone.utc).date().isoformat()
    last_alive = state.get("last_alive", today) if state else today
    # Touch the file weekly so GitHub keeps the schedule alive (it pauses after 60 idle days).
    if (datetime.fromisoformat(today) - datetime.fromisoformat(last_alive)).days >= 7:
        last_alive = today
    save_state(seen, last_alive)

    if not new_matches:
        print("No new matching jobs. Staying quiet.")
        return

    count = len(new_matches)
    if first_run:
        subject = f"Affirm alert bot is live: {count} matching job(s) open right now"
    else:
        subject = f"{count} new Affirm job(s) for you"
    body = "\n\n".join(format_job(j, n) for j, n in new_matches)
    print(subject)
    print(body)

    create_issue(subject, body)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # make failures visible in the Actions log
        print(f"Error: {exc}", file=sys.stderr)
        raise
