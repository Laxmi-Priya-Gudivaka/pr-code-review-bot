#!/usr/bin/env python3
"""
Simple automated PR code-review script.

Current rule:
  • For every changed Java file (.java) in the pull request diff,
    warn if the diff contains the text 'System.out.println'.
"""

import os
import json
from github import Github

# ---------------------------------------------------------------------------
# 1) Authenticate to GitHub
# ---------------------------------------------------------------------------
token = os.getenv("GITHUB_TOKEN")
if not token:
    raise RuntimeError("GITHUB_TOKEN not found in environment")

gh = Github(token)

# ---------------------------------------------------------------------------
# 2) Read event payload to get repo + PR number
#    (more reliable than parsing GITHUB_REF)
# ---------------------------------------------------------------------------
event_path = os.getenv("GITHUB_EVENT_PATH")
if not event_path:
    raise RuntimeError("GITHUB_EVENT_PATH not found")

with open(event_path, "r", encoding="utf-8") as fp:
    event = json.load(fp)

pr_number = event["pull_request"]["number"]              # int
repo_name = os.getenv("GITHUB_REPOSITORY")               # e.g. user/repo

repo = gh.get_repo(repo_name)
pr = repo.get_pull(pr_number)

print(f"Reviewing PR #{pr_number} in {repo_name}")

# ---------------------------------------------------------------------------
# 3) Analyse changed files
# ---------------------------------------------------------------------------
comments_to_post = []

for file in pr.get_files():
    # Only look at Java source files
    if not file.filename.endswith(".java"):
        continue

    patch = file.patch or ""     # diff hunks as a single string
    if "System.out.println" in patch:
        # NOTE: 'position' is the line index *in the diff*, 1-based.
        # For a demo we use position=1.  For production you would parse
        # 'patch' to locate the exact hunk/line containing the offence.
        comments_to_post.append(
            {
                "path": file.filename,
                "position": 1,
                "body": (
                    "⚠️ **Avoid using `System.out.println`.** "
                    "Please use a logging framework (e.g., `java.util.logging`, "
                    "`slf4j`, `Log4j`) instead."
                ),
            }
        )

# ---------------------------------------------------------------------------
# 4) Post inline review comments
# ---------------------------------------------------------------------------
if comments_to_post:
    for comment in comments_to_post:
        try:
            pr.create_review_comment(**comment)
            print(f"Commented on {comment['path']}")
        except Exception as exc:
            print(f"Failed to post comment on {comment['path']}: {exc}")
else:
    print("No issues found – no comments posted.")
