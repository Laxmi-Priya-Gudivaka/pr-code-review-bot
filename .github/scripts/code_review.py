#!/usr/bin/env python3
"""
Automated PR review: warns about 'System.out.println' in Java files.
Workflow fails (exit code 1) if any warning is posted.
"""

import os, json, sys
from github import Github

# ---------------------------------------------------------------------------
# 1. authenticate
# ---------------------------------------------------------------------------
token = os.getenv("GITHUB_TOKEN")
gh = Github(token)

# ---------------------------------------------------------------------------
# 2. get repo + PR number from event payload
# ---------------------------------------------------------------------------
with open(os.getenv("GITHUB_EVENT_PATH"), encoding="utf-8") as fp:
    event = json.load(fp)

repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = event["pull_request"]["number"]

repo = gh.get_repo(repo_name)
pr   = repo.get_pull(pr_number)
head_sha = pr.head.sha  # needed for inline review comments

print(f"Reviewing PR #{pr_number} in {repo_name}")

# ---------------------------------------------------------------------------
# 3. scan changed files
# ---------------------------------------------------------------------------
review_comments = []   # will be fed to create_review()

for file in pr.get_files():
    if not file.filename.endswith(".java"):
        continue

    patch = file.patch or ""
    if "System.out.println" in patch:
        review_comments.append(
            {
                "path": file.filename,
                "line": 1,           # demo ⇒ first line; refine later
                "side": "RIGHT",     # comment on the new code
                "body": (
                    "⚠️ **Avoid `System.out.println`.** "
                    "Use a logging framework such as SLF4J or Log4j."
                ),
            }
        )

# ---------------------------------------------------------------------------
# 4. post review (if needed)
# ---------------------------------------------------------------------------
if review_comments:
    pr.create_review(
        body="Automated review found issues.",
        event="REQUEST_CHANGES",
        comments=review_comments,
        commit=head_sha,
    )
    print(f"Posted {len(review_comments)} comment(s) and requested changes.")
    sys.exit(1)   # make the workflow fail
else:
    print("No issues detected.")
