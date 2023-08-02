import requests
from _secrets import GITHUB_TOKEN, GITHUB_COMMIT_URL
from debug_logger import DebugLogger

initial_run_sha = 0

    
def set_initial_run_sha():
    global initial_run_sha
    initial_run_sha = get_latest_commit_sha()
    print(f"Initial run sha: {initial_run_sha}")

    debug_logger = DebugLogger.get_instance()
    debug_logger.log(f"Initial run sha: {initial_run_sha}")

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
        debug_logger = DebugLogger.get_instance()
        debug_logger.log(f"[New Version Detected] Initiating the update and restart process...\n[{initial_run_sha}] -> [{check_sha}]")
        try:
            await bot.close()
        except:
            pass