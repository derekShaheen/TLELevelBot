from yaml import safe_load, safe_dump
from os import makedirs, path, walk


def load_user_data(guild_id, user_id):
    default_user_data = {'level': 1, 'experience': 0, 'points_in_last_minute': 0}
    # Create the guild directory if it doesn't exist
    makedirs(f'data/{guild_id}', exist_ok=True)
    # Load the user's data if it exists, otherwise create a new data file
    if path.exists(f'data/{guild_id}/{user_id}.yaml'):
        with open(f'data/{guild_id}/{user_id}.yaml', 'r') as file:
            return safe_load(file)
    else:
        with open(f'data/{guild_id}/{user_id}.yaml', 'w') as file:
            safe_dump(default_user_data, file)
        return default_user_data

def load_all_user_data(guild_id):
    # Create the guild directory if it doesn't exist
    makedirs(f'data/{guild_id}', exist_ok=True)
    # Initialize the user data list
    user_data_list = []
    # Walk the guild directory and load each user's data
    for root, dirs, files in walk(f'data/{guild_id}'):
        for file in files:
            if file.endswith('.yaml') and file != 'guild_data.yaml':
                with open(path.join(root, file), 'r') as f:
                    user_data = safe_load(f)
                    user_data_list.append((file.replace('.yaml', ''), user_data))
    # Sort the list by user experience
    user_data_list.sort(key=lambda x: x[1]['experience'], reverse=True)
    return user_data_list

def save_user_data(guild_id, user_id, data):
    with open(f'data/{guild_id}/{user_id}.yaml', 'w') as file:
        safe_dump(data, file)

def load_guild_data(guild_id):
    # Load the guild's data if it exists, otherwise create a new data file
    if path.exists(f'data/{guild_id}/guild_data.yaml'):
        with open(f'data/{guild_id}/guild_data.yaml', 'r') as file:
            return safe_load(file)
    else:
        data = {
            'leaderboard': None, 
            'leaderboard_message': None, 
            'level_roles': None, 
            'levelup_log': None,
            'levelup_log_message': None,
            'publog': None
        }
        # Create guild directory if it doesn't exist
        makedirs(f'data/{guild_id}', exist_ok=True)
        # Create guild_data.yaml
        with open(f'data/{guild_id}/guild_data.yaml', 'w') as file:
            safe_dump(data, file)
        return data


def save_guild_data(guild_id, data):
    data = {k: data[k] for k in sorted(data)} # Sort the data before saving
    with open(f'data/{guild_id}/guild_data.yaml', 'w') as file:
        safe_dump(data, file)

def load_config():
    default_config = {
        'chat_limit': 5,
        'experience_per_chat': 25,
        'experience_per_minute_voice': 10,
        'experience_constant': 1.5,
        'experience_streaming_bonus': 1
    }
    # Create data directory if it doesn't exist
    makedirs(f'data/', exist_ok=True)
    # Load the config file if it exists, otherwise create a new config file
    if path.exists('data/config.yaml'):
        with open('data/config.yaml', 'r') as file:
            return safe_load(file)
    else:
        with open('data/config.yaml', 'w') as file:
            safe_dump(default_config, file)
        return default_config
