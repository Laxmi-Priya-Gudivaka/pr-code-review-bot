import os
from github import Github

token = os.getenv("GITHUB_TOKEN")
g = Github(token)

repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("GITHUB_REF").split('/')[-1]

repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))

comments = []

for file in pr.get_files():
    if file.filename.endswith(".java"):
        patch = file.patch or ""
        if "System.out.println" in patch:
            comments.append({
                "path": file.filename,
                "position": 1,  # This may need to be adjusted for real-world diffs
                "body": "⚠️ Avoid using `System.out.println`; consider using a logger instead."
            })

for comment in comments:
    try:
        pr.create_review_comment(**comment)
    except Exception as e:
        print(f"Error posting comment: {e}")
