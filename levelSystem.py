from configManager import load_guild_data, load_config, save_user_data, load_user_data, save_guild_data
import discord
import math
from functools import lru_cache
from os import path
import glob
import discord

import asciichartpy
import pandas as pd
from datetime import datetime
from util import get_random_color, get_celebration_emoji
from debug_logger import DebugLogger

async def process_experience(ctx, guild, member, experience_addition, debug = False):
    debug_logger = DebugLogger.get_instance()
    user_data = load_user_data(guild.id, member.id)
    if user_data.get('blacklisted'):
        debug_logger.log("➥ Issued 0xp to {member.name} [blacklisted].")
        return
    
    # Current level
    current_level = user_data['level']

    # Don't issue experience if the member's status is idle
    if member.status == discord.Status.idle and member.voice and member.voice.channel:
        debug_logger.log("➥ Issued 0xp to {member.name} [idle]. Experience: {round(user_data['experience'] + experience_addition, 2)}, Level: {current_level}")
        return
    
    # Add a bonus if the member has boosted the server 
    if discord.utils.get(member.roles, name='Server Booster') is not None:
        experience_addition *= 1.1

    experience_addition = round(experience_addition, 2)
    # Add the experience to the user's total
    user_data['experience'] = round(user_data['experience'] + experience_addition, 2)
    if user_data['experience'] < 0:
        user_data['experience'] = 0

    # Calculate new level
    new_level = calculate_level(user_data['experience'])
    user_data['level'] = new_level

    # Save user data
    save_user_data(guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(guild, new_level, member)
    
    debug_logger.log(f"➥ Issued {experience_addition}xp to {member.name}. Experience: {round(user_data['experience'] + experience_addition, 2)}, New Level: {new_level}, Prior Level: {current_level}")
    if current_level != new_level:
        await log_level_up(ctx, guild, member, new_level)

    return new_level

async def generate_leaderboard(bot, guild_id):
    user_data_files = glob.glob(f'data/{guild_id}/[!guild_data]*.yaml')

    user_data_list = []
    for user_data_file in user_data_files:
        user_id = path.splitext(path.basename(user_data_file))[0]
        user_data = load_user_data(guild_id, user_id)
        user_data_list.append((user_id, user_data))

    user_data_list.sort(key=lambda item: item[1]['experience'], reverse=True)

    leaderboard_data = []
    leaderboard_levels = []
    min_level = 9999
    max_level = 0
    max_username_len = 0
    rank_emoji = ["🥇", "🥈", "🥉"] + ["🏅"]*2 + ["🔹"]*2 + ["🔸"]*2 + [""]*10
    for rank, (user_id, user_data) in enumerate(user_data_list[:9], start=1):
        user = await bot.fetch_user(int(user_id))
        username = user.display_name or user.name
        username = username[0].upper() + username[1:]  # Capitalize the first letter
        username = f'{rank_emoji[min(rank-1, len(rank_emoji)-1)]} {username}'
        max_username_len = max(max_username_len, len(username))  # Track the maximum username length
        leaderboard_data.append((username, user_data["level"], user_data["experience"]))
        leaderboard_levels.append(user_data['level'])
        min_level = min(min_level, user_data["level"])  # Track the minimum level
        max_level = max(max_level, user_data["level"])  # Track the maximum level

    max_level_len = 0
    max_xp_len = 0
    for _, level, xp in leaderboard_data[:9]:
        max_level_len = max(max_level_len, len(str(level)))  # Track the maximum level length
        max_xp_len = max(max_xp_len, len(str(round(xp))))  # Track the maximum XP length

    # Find the next level that's lower than min_level
    next_lower_level = next((user_data['level'] for user_id, user_data in user_data_list[9:] if user_data['level'] < min_level), min_level)
    stretched_leaderboard_levels = [lvl for lvl in leaderboard_levels for _ in range(3)]
    stretched_leaderboard_levels.append(next_lower_level)

    # Calculate height
    height = min(max_level - next_lower_level, 15)

    # Generate ASCII plot for levels
    ascii_plot = asciichartpy.plot(stretched_leaderboard_levels, {'format': '{:>6.0f}', 'height': height})

    # Add label
    ascii_plot = ascii_plot + '\n\n\t\tTop 9 Users by Level'

    # Add user labels to the plot, pad usernames to align level and XP info
    for username, level, xp in leaderboard_data[:9]:
        level_str = str(level).rjust(max_level_len)
        xp_str = str(round(xp)).rjust(max_xp_len)
        #ascii_plot += '\n' + username.ljust(max_username_len) + f'  (Level: {level_str} Rep: {xp_str})'
        ascii_plot += '\n' + username.ljust(max_username_len) + f'  Rep Level: {level_str}'


    # Add label
    ascii_plot = '   Level\n' + ascii_plot

    # Add title
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:00]")
    ascii_plot = '\n\t\t\t' + timestamp + '\n   Earn Rep by participating in the server!\n' + ascii_plot

    # Return the ASCII plot
    return ascii_plot


#@lru_cache(maxsize=None)  # Unbounded cache, you may want to restrict the size in a real application
def calculate_level(experience, debug = False):
    # Get experience constant from config
    config = load_config()
    experience_constant = config['experience_constant']
    
    # Using the formula: level = (level * math.pow((level, experience_constant)) + 30)
    level = 1
    while experience >= (level * (math.pow(level, experience_constant)) + 30):
        if debug:
            # Print on one line
            print(f"Level: {level}, Experience: {experience}, Change: {(level * (math.pow(level, experience_constant)) + 30)}")
        experience -= (level * (math.pow(level, experience_constant)) + 30)
        level += 1
    
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
                debug_logger.log(f"Added role id: {role_id} to member id: {member.id}")
            # Remove role if level is above new level
            elif level > new_level and role in member.roles:
                await member.remove_roles(role)
                debug_logger.log(f"Removed role id: {role_id} from member id: {member.id}")
    else:
        debug_logger.log(f"No 'level_roles' found in guild data for guild id: {guild.id}")

async def log_level_up(ctx, guild, member, new_level):
    if 1 < new_level <= 5:  # Don't log for levels >1 and <=5
        return

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

    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")
    member_name = member.name[0].upper() + member.name[1:]  # Capitalize member's name
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
    
    debug_logger = DebugLogger.get_instance()
    debug_logger.log(f"({guild.name}) {new_levelup_text}")