import importlib
import subprocess
import sys
import random

import discord
from datetime import time, timedelta, datetime
import pytz
import math
from _secrets import DEVELOPER_ID

def verify_libraries_installed(libraries):
    for library in libraries:
        try:
            importlib.import_module(library[0])
        except ImportError:
            print(f"{library[0]} not installed. Installing...")
            subprocess.call([sys.executable, "-m", "pip", "install", library[1]])

# async def send_embed(ctx, title, description, color):
#     embed = discord.Embed(title=title, description=description, color=color)
#     await ctx.send(embed=embed)

async def send_embed(recipient, title, description, color, url=None, fields=None, file=None, thumbnail_url=None):
    embed = discord.Embed(
        title=title, description=description, color=color, url=url)
    embed.timestamp = discord.utils.utcnow()

    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)

    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

    if file:
        await recipient.send(embed=embed, file=file)
    else:
        await recipient.send(embed=embed)

def get_initial_delay(target_time: time = None, interval: timedelta = None) -> float:
    now = datetime.now(pytz.timezone('America/Chicago'))

    if target_time:
        # Schedule task at the target time
        if now.time() >= target_time:
            tomorrow = now.date() + timedelta(days=1)
        else:
            tomorrow = now.date()
        next_run = datetime.combine(
            tomorrow, target_time, tzinfo=now.tzinfo)
    elif interval:
        # Schedule task at the next interval
        interval_seconds = interval.total_seconds()
        elapsed_time = (now - now.replace(hour=0, minute=0,
                        second=0, microsecond=0)).total_seconds()
        next_run_seconds = math.ceil(
            elapsed_time / interval_seconds) * interval_seconds
        next_run = now.replace(hour=0, minute=0, second=0,
                               microsecond=0) + timedelta(seconds=next_run_seconds)

    return (next_run - now).total_seconds()

def get_random_color(noReds = False):
    if noReds:
        color_list = [
            "default", "teal", "green", "blue", "purple", "magenta", "gold", "blurple",
            # "dark_teal", "dark_green", "dark_blue", "dark_purple",
            # "dark_magenta", "dark_gold", "dark_orange",
            # "lighter_grey", "dark_grey", "light_grey", "darker_grey", "greyple"
        ]
    else:
        color_list = [
            "default", "teal", "green", "blue", "purple", "magenta", "gold", "orange", "red", "blurple",
            # "dark_teal", "dark_green", "dark_blue", "dark_purple",
            # "dark_magenta", "dark_gold", "dark_orange", "dark_red",
            # "lighter_grey", "dark_grey", "light_grey", "darker_grey", "greyple"
        ]
    random_color_name = random.choice(color_list)
    return getattr(discord.Color, random_color_name)()

async def send_developer_message(client, title, description, color, file=None, fields=None):
    """Send a private message to the developer as an embed."""
    # Fetch the developer's user object using their ID
    developer = await client.fetch_user(DEVELOPER_ID)

    # Create the embed
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)

    # Send the embed with the image (if provided) to the developer
    if file:
        await send_embed(developer, title, description, color, None, fields, file)
    else:
        await send_embed(developer, title, description, color, None, fields)