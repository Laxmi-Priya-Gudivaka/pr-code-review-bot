#!/usr/bin/env python3
"""
Automated PR review:
  – Flags 'System.out.println' in changed Java files.
  – Requests changes and fails the workflow when a violation is found.
"""

import os, json, sys
from github import Github

# ---------------------------------------------------------------------------
# 1. authenticate
# ---------------------------------------------------------------------------
token = os.getenv("GITHUB_TOKEN")
gh = Github(token)

# ---------------------------------------------------------------------------
# 2. get repo + PR info from event payload
# ---------------------------------------------------------------------------
with open(os.getenv("GITHUB_EVENT_PATH"), encoding="utf-8") as f:
    event = json.load(f)

repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = event["pull_request"]["number"]

repo = gh.get_repo(repo_name)
pr   = repo.get_pull(pr_number)

print(f"Reviewing PR #{pr_number} in {repo_name}")

# ---------------------------------------------------------------------------
# 3. scan diff for violations
# ---------------------------------------------------------------------------
review_comments = []

for file in pr.get_files():
    if not file.filename.endswith(".java"):
        continue

    patch = file.patch or ""
    if "System.out.println" in patch:
        review_comments.append(
            {
                "path": file.filename,
                "line": 1,           # demo line; refine later
                "side": "RIGHT",
                "body": (
                    "⚠️ **Avoid `System.out.println`.** "
                    "Use a proper logging framework instead."
                ),
            }
        )

# ---------------------------------------------------------------------------
# 4. post review & set exit status
# ---------------------------------------------------------------------------
if review_comments:
    pr.create_review(
        body="Automated review found issues.",
        event="REQUEST_CHANGES",
        comments=review_comments
        # commit param omitted → default head commit is used
    )
    print(f"Posted {len(review_comments)} comment(s); requested changes.")
    sys.exit(1)          # make the workflow fail
else:
    print("No issues detected.")
