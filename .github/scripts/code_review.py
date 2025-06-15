#!/usr/bin/env python3
"""
AI-powered PR code review (OpenRouter)

• Scans every changed .java file in the PR.
• Sends full file content to an OpenRouter model.
• Expects JSON list [{"line": int, "message": str}, …].
• Posts inline review comments and requests changes.
• Fails the workflow (exit 1) when issues are found.
"""

import os
import sys
import json
from github import Github
from openai import OpenAI


def main() -> int:
    # required env vars
    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")
    gh_token  = os.getenv("GITHUB_TOKEN")
    or_key    = os.getenv("OPENROUTER_AI_API_KEY")

    if not all([repo_name, pr_number, gh_token, or_key]):
        print("❌ Missing environment variables "
              "(GITHUB_REPOSITORY, PR_NUMBER, GITHUB_TOKEN, OPENROUTER_AI_API_KEY)")
        return 1

    pr_number = int(pr_number)

    # GitHub client
    gh   = Github(gh_token)
    repo = gh.get_repo(repo_name)
    pr   = repo.get_pull(pr_number)

    # OpenRouter client via OpenAI SDK
    client = OpenAI(
        api_key = or_key,
        base_url = "https://openrouter.ai/api/v1"
    )

    issues_found = False
    issues_by_file = {}

    # iterate over changed .java files
    for f in pr.get_files():
        if not f.patch or not f.filename.endswith(".java"):
            continue

        try:
            file_content_bytes = repo.get_contents(f.filename, ref=pr.head.ref).decoded_content
            file_content = file_content_bytes.decode()
        except Exception as e:
            print(f"❌ Failed to fetch file content for {f.filename}: {e}")
            continue

        prompt = f"""
You are a senior Java code reviewer. Analyze the code below and return ONLY a JSON array of objects with this format:

[
  {{"line": 12, "message": "Avoid using raw types like 'List'. Use generics instead."}},
  ...
]

Rules:
- Focus on best practices, performance, maintainability, and modern Java usage (Java 8+).
- Point out outdated practices or bad design patterns (like nested loops, magic numbers, duplicate logic, hardcoded values, tight coupling, etc.).
- Do not write explanations. Just JSON list. Return an empty list [] if nothing is found.

```java
{file_content}
```"""


        try:
            resp = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0,
            )
            raw_output = resp.choices[0].message.content.strip()

            # Clean markdown backticks if present
            if raw_output.startswith("```"):
                raw_output = "\n".join(raw_output.split("\n")[1:-1]).strip()

            print(f"🔎 Raw model output from {f.filename}:\n{raw_output}\n")

            feedback = json.loads(raw_output)

            if feedback:
                issues_found = True
                issues_by_file.setdefault(f.filename, []).extend(feedback)

        except Exception as e:
            print(f"❌ OpenRouter call/parsing failed for {f.filename}: {e}")
            return 1

    # create PR comment if issues were found
    if issues_found:
        comment_body = "🔴 **Automated review found issues:**\n\n"
        for filename, issues in issues_by_file.items():
            comment_body += f"**File: `{filename}`**\n"
            for issue in issues:
                comment_body += f"- Line {issue['line']}: {issue['message']}\n"
            comment_body += "\n"
        comment_body += "Please address these issues before merging."

        pr.create_issue_comment(comment_body)
        print("🔴 Comment with issues posted – failing job.")
        return 1

    # no issues
    pr.create_issue_comment("✅ Automated review: no issues found.")
    print("🟢 No issues found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
