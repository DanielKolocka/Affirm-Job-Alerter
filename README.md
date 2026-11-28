# Affirm job alert bot

Checks Affirm's job board every 3 hours on GitHub Actions. When a **new** non senior engineering or early career role shows up in Canada, it opens an issue in this repo, and GitHub emails you about it. If nothing new appears, you get one short daily check-in instead, so you know it's still running.

No apps, no extra accounts, no passwords. It only uses your GitHub account.

The very first run opens one issue listing every matching job open right now. After that you only hear about new ones.

## Daily check-in

Once a day, around 7 AM Vancouver time (8 AM in summer), the bot comments on a single **Bot status: daily check-in** issue saying it is still running and how many times it checked. GitHub emails you each comment. On days when you already got a new job alert, it skips the check-in, since the alert proves it's running.

Change `HEARTBEAT_HOUR_UTC` at the top of `check_jobs.py` to move it. If you ever stop getting the check-in, look at the **Actions** tab for a failed run.

## What counts as a match

| Rule | Example kept | Example dropped |
|---|---|---|
| Title has engineer, developer, early career or new grad | Software Engineer I, Frontend | Quantitative Analyst II |
| Not an internship or co-op | Software Engineer, Early Career | Software Engineer Intern |
| Title is not senior | Machine Learning Engineer II | Senior / Staff / Principal / Lead / Manager / III |
| Location is in Canada | Remote Canada, Toronto | Remote US, San Francisco, Remote UK |

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
