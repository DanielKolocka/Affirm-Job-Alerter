# Affirm job alert bot

Checks Affirm's job board every 3 hours on GitHub Actions. When a **new** non senior engineering or early career role shows up in Canada or the US, it opens an issue in this repo, and GitHub emails you about it. If nothing new appears, it stays quiet.

No apps, no extra accounts, no passwords. It only uses your GitHub account.

The very first run opens one issue listing every matching job open right now. After that you only hear about new ones.

## What counts as a match

| Rule | Example kept | Example dropped |
|---|---|---|
| Title has engineer, developer, early career, new grad, intern or co-op | Software Engineer I, Frontend | Quantitative Analyst II |
| Title is not senior | Machine Learning Engineer II | Senior / Staff / Principal / Lead / Manager / III |
| Location is Canada or US | Remote Canada, San Francisco | Remote Poland, Remote UK |

US roles are kept, but the alert adds a note when the posting says something like "we do not sponsor visas" or "must be authorized to work in the US", so you can tell at a glance if a Canadian can apply.

Tweak the word lists at the top of `check_jobs.py` if you want to widen or narrow it.

## Setup (about 3 minutes)

1. Create a new **private** repo on GitHub (for example `affirm-job-alerts`) and upload these files, keeping the folder structure:
   ```
   check_jobs.py
   README.md
   .github/workflows/check-jobs.yml
   ```
2. In the repo, open the **Actions** tab, pick **Check Affirm jobs**, and press **Run workflow**.

You should get an email from GitHub within a minute or two, titled "Affirm alert bot is live". From then on it runs by itself every 3 hours.

**Not getting the email?** Check https://github.com/settings/notifications and make sure **Email** is ticked under "Participating, @mentions and custom". Also check your spam folder the first time.

**Phone alerts (optional):** if you ever install the GitHub mobile app, you'll get these as push notifications too. You don't need it.

Close an issue once you've looked at the jobs, or leave them open as a list of what you want to apply to.
