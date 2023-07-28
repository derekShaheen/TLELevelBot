import discord
from datetime import time, timedelta, datetime
import pytz
import math

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