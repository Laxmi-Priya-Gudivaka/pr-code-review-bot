#!/usr/bin/env python3
"""
CI code review:
– Adds inline comments on 'System.out.println' in .java files.
– Fails the job if such patterns are found.
"""

import os, json, sys
from github import Github

gh = Github(os.getenv("GITHUB_TOKEN"))

# Get PR number from event
with open(os.getenv("GITHUB_EVENT_PATH")) as f:
    event = json.load(f)

repo_name = os.getenv("GITHUB_REPOSITORY")
repo = gh.get_repo(repo_name)
pr_number = event["pull_request"]["number"]
pr = repo.get_pull(pr_number)

print(f"Reviewing PR #{pr.number}")

violations = []

# Check changed files
for f in pr.get_files():
    if f.filename.endswith(".java") and "System.out.println" in (f.patch or ""):
        print(f"Issue found in {f.filename}")
        violations.append({
            "path": f.filename,
            "body": "⚠️ Avoid `System.out.println`; use a logger instead.",
            "position": 1  # You can refine this to exact line later
        })

# Post inline comments
for v in violations:
    pr.create_review_comment(**v)
    print(f"Commented on {v['path']}")

# Fail job if any comments were made
if violations:
    print("Violations found — failing job.")
    sys.exit(1)
else:
    print("No issues found.")
