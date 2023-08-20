from configManager import load_guild_data, load_config, save_user_data, load_user_data, save_guild_data
import discord
import math
from functools import lru_cache
from os import path
import glob
import discord

import asciichartpy
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from util import get_random_color, get_celebration_emoji, add_commas
from debug_logger import DebugLogger

async def process_experience(ctx, guild, member, debug=False, source=None, message=None):
    if source == 'voice_activity':
        if not member.voice:
            return 0 # Do not issue experience if the member is not in a voice channel, and the source is voice activity
        
    debug_logger = DebugLogger.get_instance()
    user_data = load_user_data(guild.id, member.id)
    config = load_config()
    
    # If the source is "on_ready"
    # Calculate the level and make sure it matches the xp gained, adjust roles, do not issue experience.
    if source == "on_ready":
        if user_data['experience'] == 0: # If the user has no experience, do not process
            return 0
        
        calculated_level = calculate_level(user_data['experience'])
        await adjust_roles(guild, calculated_level, member)
        # If the calculated level does not match the stored level, update the stored level
        if user_data['level'] != calculated_level:
            user_data['level'] = calculated_level
            save_user_data(guild.id, member.id, user_data)

        return user_data['level']
    
    if user_data.get('blacklisted'):
        debug_logger.log("➥ Issued 0r to {member.name} [blacklisted].")
        return 0

    # Current level
    current_level = user_data['level']
    experience_gain = 0
    if source == 'voice_activity':
        if member.voice and member.voice.channel and (member.voice.channel.id != guild.afk_channel.id):
            is_alone = len(member.voice.channel.members) == 1
            is_idle = (member.voice.self_mute and member.voice.self_deaf) or member.status == discord.Status.idle or member.status == discord.Status.offline
            all_others_idle = all((other_member.status == discord.Status.idle or
                                    (other_member.voice.self_mute and other_member.voice.self_deaf)) for other_member in member.voice.channel.members if other_member != member)
            
            if member.voice.self_stream:
                experience_gain += config['experience_streaming_bonus']
            if is_alone:
                experience_gain += config['experience_per_minute_voice'] / 4
            elif is_idle:
                experience_gain += config['experience_per_minute_voice'] / 4
            elif all_others_idle:
                experience_gain += config['experience_per_minute_voice'] / 3
            else:
                experience_gain += config['experience_per_minute_voice']
            
            # Don't issue experience if the member's status is idle
            if member.status == discord.Status.idle:
                experience_gain = 1   
    elif source == 'chat':
        now = datetime.now()
        user_data['chats_timestamps'] = [timestamp for timestamp in user_data['chats_timestamps'] if now - timestamp < timedelta(minutes=3)]
        num_chats = len(user_data['chats_timestamps'])
        user_data['chats_timestamps'].append(now)
        experience_gain = max(1, config['experience_per_chat'] * (1 - num_chats / config['chat_limit']))
        if message.author.voice and message.author.voice.channel:
            experience_gain /= 3
    else:
        debug_logger.log(f"Invalid source provided to process_experience: {source}")
        return 0

    # No changes, return
    if experience_gain == 0:
        return current_level

    if discord.utils.get(member.roles, name='Server Booster') is not None:
        experience_gain *= 1.1

    experience_gain = round(experience_gain, 2)
    user_data['experience'] = round(user_data['experience'] + experience_gain, 2)
    if user_data['experience'] < 0:
        user_data['experience'] = 0

    # Calculate new level
    new_level = calculate_level(user_data['experience'])
    user_data['level'] = new_level

    # Determine the username, save it to their data for future reference
    username = member.display_name or member.nick or member.name
    user_data['username'] = username  # Update the user_data with the username

    # Save user data
    save_user_data(guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(guild, new_level, member)

    debug_logger.log(f"{experience_gain}r ➥ {member.name}. Rep: {add_commas(round(user_data['experience'] + experience_gain, 2))}, New Level: {new_level}, Prior Level: {current_level}")
    if current_level != new_level:
        await log_level_up(ctx, guild, member, new_level)

    return new_level

async def generate_leaderboard(bot, guild_id, full_board = False):
    leader_depth = 9
    if full_board:
        leader_depth = 999

    user_data_files = glob.glob(f'data/{guild_id}/[!guild_data]*.yaml')

    user_data_list = []
    for user_data_file in user_data_files:
        user_id = path.splitext(path.basename(user_data_file))[0]
        user_data = load_user_data(guild_id, user_id)
        user_data_list.append((user_id, user_data))

    user_data_list.sort(key=lambda item: item[1]['experience'], reverse=True)

    guild = bot.get_guild(guild_id)

    leaderboard_data = []
    leaderboard_levels = []
    min_level = 9999
    max_level = 0
    max_username_len = 0
    rank_emoji = ["🥇", "🥈", "🥉"] + ["🏅"]*2 + ["🔹"]*2 + ["🔸"]*2
    for rank, (user_id, user_data) in enumerate(user_data_list[:leader_depth], start=1):
        #Skip user if they have less than 5 experience
        if user_data["experience"] <= 5:
            continue

        user = await guild.fetch_member(int(user_id))# -- PULL FROM GUILD
        username = user.display_name or user.nick or user.name
        username = username.title()  # Titlize the username

        # Check if rank exceeds the length of rank_emoji
        if rank <= len(rank_emoji):
            emoji = rank_emoji[rank-1]
        else:
            emoji = "➖"
        
        if not full_board:
            username = f'{emoji} {username}'
        else:
            username = f'{emoji} {rank}. {username}'

        max_username_len = max(max_username_len, len(username))  # Track the maximum username length
        leaderboard_data.append((username, user_data["level"], user_data["experience"]))
        leaderboard_levels.append(user_data['level'])
        min_level = min(min_level, user_data["level"])  # Track the minimum level
        max_level = max(max_level, user_data["level"])  # Track the maximum level

    max_level_len = 0
    max_xp_len = 0
    for _, level, xp in leaderboard_data[:leader_depth]:
        max_level_len = max(max_level_len, len(str(level)))  # Track the maximum level length
        max_xp_len = max(max_xp_len, len(str(round(xp))))  # Track the maximum XP length

    if not full_board:
        stretched_leaderboard_levels = [lvl for lvl in leaderboard_levels for _ in range(3)]
    else:
        stretched_leaderboard_levels = leaderboard_levels

    if not full_board:
        # Find the next level that's lower than min_level
        next_lower_level = next((user_data['level'] for user_id, user_data in user_data_list[leader_depth:] if user_data['level'] < min_level), min_level)
        stretched_leaderboard_levels.append(next_lower_level)

    # Calculate height
    if not full_board:
        height = min(max_level - next_lower_level, 16)

    # Generate ASCII plot for levels
    if full_board:
        ascii_plot = asciichartpy.plot(stretched_leaderboard_levels, {'format': '{:>6.0f}'})
    else:
        ascii_plot = asciichartpy.plot(stretched_leaderboard_levels, {'format': '{:>6.0f}', 'height': height})

    # Add label
    if full_board:
        ascii_plot = ascii_plot + '\n\n\t\tTop Users by Level'
    else:
        ascii_plot = ascii_plot + '\n\n\t\tTop 9 Users by Level'

    # Add user labels to the plot, pad usernames to align level and XP info
    for username, level, xp in leaderboard_data[:leader_depth]:
        level_str = str(level).rjust(max_level_len)
        xp_str = str(round(xp)).rjust(max_xp_len)
        if not full_board:
            ascii_plot += '\n' + username.ljust(max_username_len) + f'  Rep Level: {level_str}'
        else:
            ascii_plot += '\n' + username.ljust(max_username_len) + f'  (Level: {level_str} Rep: {xp_str})'


    # Add label
    ascii_plot = '   Level\n' + ascii_plot

    # Add title
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:00]")
    ascii_plot = '\n\t\t\t' + timestamp + '\n   Earn Rep by participating in the server!\n' + ascii_plot

    # Return the ASCII plot
    return ascii_plot

# Generate a matplotlib image of the leaderboard. Too many characters can be returned with the other function for discord to handle. Let's try an image
async def generate_leaderboard_image(bot, guild_id, full_board=False):
    leader_depth = 9
    if full_board:
        leader_depth = 999

    user_data_files = glob.glob(f'data/{guild_id}/[!guild_data]*.yaml')

    user_data_list = []
    for user_data_file in user_data_files:
        user_id = path.splitext(path.basename(user_data_file))[0]
        user_data = load_user_data(guild_id, user_id)
        user_data_list.append((user_id, user_data))

    user_data_list.sort(key=lambda item: item[1]['experience'], reverse=True)

    guild = bot.get_guild(guild_id)

    usernames = []
    levels = []

    for rank, (user_id, user_data) in enumerate(user_data_list[:leader_depth], start=1):
        if user_data.get('experience') <= 5:
            continue

        user = guild.get_member(int(user_id))
        if user:
            username = user.display_name or user.nick or user.name
            username = username.title()
        else:
            continue
        # elif user_data.get('username') is not None:
        #     username = user_data['username']
        # else:
        #     username = user_id

        if not full_board:
            username = f'{username}'
            username = f'{rank}. {username}'

        usernames.append(username)
        levels.append(user_data["level"])

    # Create pyplot figure and axes
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(usernames[::-1], levels[::-1], color='skyblue')  # Reverse to have the top player at the top

    # Customize the plot
    ax.set_xlabel('Levels')
    ax.set_title(f'Leaderboard by Level')
    plt.tight_layout()

    # Save the plot to an image file
    image_path = f'data/{guild_id}/leaderboard.png'
    plt.savefig(image_path)

    # Close the plot
    plt.close()

    return image_path


def calculate_level(experience, debug = False):
    # # Get experience constant from config
    # config = load_config()
    # experience_constant = config['experience_constant']
    
    # # Using the formula: level = (level * math.pow((level, experience_constant)) + 30)
    # level = 1
    # while experience >= (level * (math.pow(level, experience_constant)) + 30):
    #     if debug:
    #         # Print on one line
    #         print(f"Level: {level}, Experience: {experience}, Change: {(level * (math.pow(level, experience_constant)) + 30)}")
    #     experience -= (level * (math.pow(level, experience_constant)) + 30)
    #     level += 1
    
    # return level
    # v2 Below
    global experience_cache  # Access the global variable

    # Ensure we have cached enough experience values for this calculation
    while experience > experience_cache[-1]:
        # If we need to expand the list, do it by 10 levels at a time
        cumulative_experience_for_level(len(experience_cache) + 10)

    # Search through the cache for the level
    level = 1
    for i in range(1, len(experience_cache)):
        if experience_cache[i] > experience:
            break
        level = i
        #if debug:
            #print(f"Level: {level}, Experience: {experience}, Change: {experience_cache[i]}")

    return level

# Initialize the experience list globally
experience_cache = [0]  # Start the list with 0 so that the indexes line up with the levels

def cumulative_experience_for_level(target_level: int):
    # Get experience constant from config
    config = load_config()
    experience_constant = config['experience_constant']

    global experience_cache  # Access the global variable

    if target_level < len(experience_cache):
        # We have the data in cache, just return it
        return experience_cache[:target_level+1]
    
    # We need to calculate more levels
    for level in range(len(experience_cache), target_level+1):
        experience_for_level = (level * (level ** experience_constant)) + 30
        total_experience = experience_cache[-1] + experience_for_level
        experience_cache.append(total_experience)

    return experience_cache

async def adjust_roles(guild, new_level, member):
    debug_logger = DebugLogger.get_instance()
    guild_data = load_guild_data(guild.id)

    if 'level_roles' in guild_data:
        level_roles = guild_data['level_roles']

        # Iterate through all level roles 
        for level_str, role_id in level_roles.items():
            level = int(level_str)
            role = discord.utils.get(guild.roles, id=role_id)

            # If role not found or doesn't change, skip this iteration
            if role is None or (role in member.roles and level <= new_level):
                continue

            # Add role if level is less or equal to new level
            if level <= new_level and role not in member.roles:
                await member.add_roles(role)
                debug_logger.log(f"Added role '{role.name}' to member '{member.name}'")
            # Remove role if level is above new level
            elif level > new_level and role in member.roles:
                await member.remove_roles(role)
                debug_logger.log(f"Removed role '{role.name}' from member '{member.name}'")
    else:
        debug_logger.log(f"No 'level_roles' found in guild data for guild '{guild.name}'")


async def log_level_up(ctx, guild, member, new_level):
    guild_data = load_guild_data(guild.id)

    levelup_log_channel_id = guild_data.get('publog')
    levelup_log_message_id = guild_data.get('levelup_log_message')
    levelup_log_channel = ctx.get_channel(levelup_log_channel_id) if levelup_log_channel_id else None
    levelup_log_message = None

    if levelup_log_channel and levelup_log_message_id:
        try:
            levelup_log_message = await levelup_log_channel.fetch_message(levelup_log_message_id)
        except discord.NotFound:
            levelup_log_message_id = None  # Reset the message ID if the message was not found

    if member is not None:
        if new_level <= 5:  # Don't log for levels >1 and <=5
            return

        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")
        member_name = member.display_name or member.nick or member.name  # Capitalize member's name
        member_name = member_name.title()
        new_levelup_text = f"{member_name} is now level {new_level}! {get_celebration_emoji()}"

        # If the levelup_log exists in guild_data, append the new level up text to the list
        # and slice the list to keep only the last 10 elements. If it does not exist, initialize it
        guild_data.setdefault('levelup_log', [])
        guild_data['levelup_log'].append((timestamp, new_levelup_text))
        guild_data['levelup_log'] = guild_data['levelup_log'][-6:]
        save_guild_data(guild.id, guild_data)

    levelup_embed = discord.Embed(
        title="Reputation Level Up Log",
        color=get_random_color(True)
    )

    # Instructions to check rank
    check_rank_instructions = "You can check your current reputation by typing `/rep`. If you want to check someone else's rep, type `/rep @username`. You can also right click on any user and go to `Apps > Show Reputation`. Try it now! All chats in this channel are cleared every hour."
    levelup_embed.add_field(name='How to check your rank:', value=check_rank_instructions, inline=False)

    for timestamp, log_text in guild_data['levelup_log']:
        levelup_embed.add_field(name=timestamp + ' ' + log_text, value='\u200b', inline=False)

    if levelup_log_message:  # If a message already exists, edit it
        await levelup_log_message.edit(embed=levelup_embed)
    else:  # If no message exists, send a new one and save its ID
        if levelup_log_channel:
            levelup_log_message = await levelup_log_channel.send(embed=levelup_embed)
            guild_data['levelup_log_message'] = levelup_log_message.id
            save_guild_data(guild.id, guild_data)
        else:
            print(f"Level up log channel not found for guild {guild.id} ({guild.name})")

    if member is not None and new_level == 6:
        embed = discord.Embed(
            title=f"{member_name}, you have reached level 6!", 
            description=f"{member.mention} Welcome to the reputation system! {get_celebration_emoji()} You gain reputation by participating in the server, and you're already level 6! We hope you enjoy your stay!", 
            color=get_random_color(True)
        )
        if levelup_log_channel:
            await levelup_log_channel.send(embed=embed)
        else:
            print(f"Level up log channel not found for guild {guild.id} ({guild.name})")
    
    debug_logger = DebugLogger.get_instance()
    if member is not None:
        debug_logger.log(f"({guild.name}) {new_levelup_text}")
    else:
        debug_logger.log(f"({guild.name}) Startup message sent/updated.")