#!/usr/bin/env python3
"""
Simplest PR-review bot:
• Scans Java diffs for 'System.out.println'.
• Posts ONE top-level PR comment listing every offending file.
• Exits 1 when it posts a warning, causing the job to fail.
"""

import os, json, sys
from github import Github

token = os.environ["GITHUB_TOKEN"]
gh = Github(token)

# event JSON gives us repo + PR number
with open(os.environ["GITHUB_EVENT_PATH"]) as f:
    ev = json.load(f)

repo = gh.get_repo(os.environ["GITHUB_REPOSITORY"])
pr    = repo.get_pull(ev["pull_request"]["number"])

violations = []

for f in pr.get_files():
    if f.filename.endswith(".java") and "System.out.println" in (f.patch or ""):
        violations.append(f.filename)

# post ONE comment if needed
if violations:
    body = (
        "🔴 **Automated review:** `System.out.println` found in these files:\n"
        + "\n".join(f"- `{v}`" for v in violations)
        + "\n\nPlease replace with a proper logger."
    )
    pr.create_issue_comment(body)
    print("Comment posted – failing job.")
    sys.exit(1)

print("No issues found.")
