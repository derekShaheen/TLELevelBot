import requests
from _secrets import GITHUB_TOKEN, GITHUB_COMMIT_URL

initial_run_sha = 0

def get_latest_commit_sha():
    url = GITHUB_COMMIT_URL
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        commits = response.json()
        latest_commit = commits[0]
        full_sha = latest_commit["sha"]
        short_sha = full_sha[:7]

        return short_sha
    else:
        print(f"Error: {response.status_code}")
        return None

async def check_version(bot, send_developer_message):
    global initial_run_sha
    check_sha = get_latest_commit_sha()

    if not check_sha.startswith('Error') and initial_run_sha != check_sha:
        title = "New bot version has been detected."
        description = f'Initiating the update and restart process...\n[{initial_run_sha}] -> [{check_sha}]'
        color = 0xff00ff
        await send_developer_message(bot, title, description, color)
        await bot.close()
