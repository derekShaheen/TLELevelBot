from util import verify_libraries_installed

libraries = [
    ("discord", "discord.py"),
    ("asyncio", "asyncio"),
    ("yaml", "PyYAML"),
    ("asciichartpy", "asciichartpy"),
    ("pandas", "pandas"),
    ("pytz", "pytz"),
    ("requests", "requests")
]

verify_libraries_installed(libraries)

import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, time
from discord.ext.commands import Greedy, Context
from typing import Literal, Optional

import _secrets
from configManager import load_user_data, load_config, save_user_data, load_guild_data, save_guild_data
from levelSystem import process_experience, generate_leaderboard
from util import get_initial_delay, get_random_color, send_developer_message
import auto_update_git

debug = True

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, reconnect=True)
config = load_config()

# Import commands after 'bot' has been initialized
from commandsAdmin import set_level, setrep, set_level_role, set_channel, blacklist
import commandsUser

bot.add_command(set_level)
bot.add_command(set_level_role)
bot.add_command(setrep)
#bot.add_command(level)
bot.add_command(set_channel)
bot.add_command(blacklist)

@bot.event
async def on_ready():
    auto_update_git.set_initial_run_sha()

    voice_activity_tracker.start()
    update_leaderboard.start()

    check_version.start()

#    await update_leaderboard()
#    await check_version()

@tasks.loop(minutes=1)
async def voice_activity_tracker():
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} Updating credits...")
    config = load_config()
    for guild in bot.guilds:
        for member in guild.members:
            # Check if the member is connected to a voice channel (but not the AFK channel)
            if member.voice and member.voice.channel and (member.voice.channel.id != guild.afk_channel.id):
                # Check if the member is alone in the voice channel
                is_alone = len(member.voice.channel.members) == 1 or (member.voice.self_mute and member.voice.self_deaf)
                # Check if all other members are idle
                all_others_idle = all((other_member.status == discord.Status.idle or (other_member.voice.self_mute and other_member.voice.self_deaf)) for other_member in member.voice.channel.members if other_member != member)
                
                experience_gain = 0

                # Check if the member is streaming
                if member.voice.self_stream:
                    experience_gain += config['experience_streaming_bonus']  # Increase experience gain if the user is streaming

                # Calculate the experience gain based on whether the member is alone, with others or with idle members only
                if is_alone:
                    experience_gain += config['experience_per_minute_voice'] / 4
                elif all_others_idle:
                    experience_gain += config['experience_per_minute_voice'] / 3
                else:
                    experience_gain += config['experience_per_minute_voice']

                # Add experience and level up if necessary
                await process_experience(bot, guild, member, experience_gain, True)
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} ...credit update complete.")



@voice_activity_tracker.before_loop
async def before_voice_activity_tracker():
    initial_delay = get_initial_delay(interval=timedelta(minutes=1))
    if debug:
        print('Update credits scheduled for: {}'.format(initial_delay))
    await asyncio.sleep(initial_delay)

@bot.event
async def on_message(message):
    # Avoid responding to bot messages
    if message.author.bot:
        return

    if message.content.startswith('!'):
        await bot.process_commands(message)
        return

    config = load_config()

    # Load or initialize user data
    user_data = load_user_data(message.guild.id, message.author.id)

    now = datetime.now()

    # Initialize 'chats_timestamps' if it doesn't exist
    if 'chats_timestamps' not in user_data:
        user_data['chats_timestamps'] = []

    # Remove timestamps older than 3 minutes
    user_data['chats_timestamps'] = [timestamp for timestamp in user_data['chats_timestamps'] if now - timestamp < timedelta(minutes=3)]
    
    # Calculate experience per chat based on number of messages sent within time limit
    num_chats = len(user_data['chats_timestamps'])

    # Add new timestamp
    user_data['chats_timestamps'].append(now)
    experience_per_chat = max(1, config['experience_per_chat'] * (1 - num_chats / config['chat_limit']))

    # Save user data after updating it
    save_user_data(message.guild.id, message.author.id, user_data)

    # Check if the user is connected to a voice channel
    if message.author.voice and message.author.voice.channel:
        # If the user is in a voice channel, penalize the experience
        experience_per_chat /= 3

    # Add experience and level up if necessary
    await process_experience(bot, message.guild, message.author, experience_per_chat, debug)

    # Process commands after checking for spam and awarding points
    await bot.process_commands(message)


@tasks.loop(minutes=60)
async def update_leaderboard():
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} Updating leaderboard...")

    for guild in bot.guilds:
        guild_data = load_guild_data(guild.id)
        leaderboard_channel_id = guild_data.get('leaderboard')
        leaderboard_channel = bot.get_channel(leaderboard_channel_id) if leaderboard_channel_id else None

        if leaderboard_channel:
            ascii_plot = await generate_leaderboard(bot, guild.id)

            leaderboard_message_id = guild_data.get('leaderboard_message')
            leaderboard_message = None

            # Try to fetch the message, but handle the error if it doesn't exist
            if leaderboard_message_id:
                try:
                    leaderboard_message = await leaderboard_channel.fetch_message(leaderboard_message_id)
                except discord.errors.NotFound:
                    leaderboard_message = None  # Reset to None if the message was not found
                    
            lb_embed = discord.Embed(
                title="Reputation Leaderboard for The Last Echelon",
                description=f"```{ascii_plot}```",
                color=get_random_color(True)
            )

            if leaderboard_message:
                #await leaderboard_message.edit(content='', embed=discord.Embed(description=f"```{ascii_plot}```"))  # Edit the old message
                await leaderboard_message.edit(embed=lb_embed)  # Edit the old message
            else:
                leaderboard_message = await leaderboard_channel.send(embed=lb_embed)  # Send a new message
                #leaderboard_message = await send_embed(leaderboard_channel, title="Leaderboard", description=f"```{ascii_plot}```", color=0x00ff00)

            guild_data['leaderboard_message'] = leaderboard_message.id
            save_guild_data(guild.id, guild_data)
    if debug:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} Update complete.")

@update_leaderboard.before_loop
async def before_update_leaderboard():
    initial_delay = get_initial_delay(interval=timedelta(hours=1, seconds=5))
    if debug:
        print('Update leaderboard scheduled for: {}'.format(initial_delay))
    await asyncio.sleep(initial_delay)

#------ Sync Tree ------
guild = discord.Object(id='262726474967023619')
# Get Guild ID from right clicking on server icon
# Must have devloper mode on discord on setting>Advance>Developer Mode
#More info on tree can be found on discord.py Git Repo
@bot.command()
@commands.guild_only()
@commands.is_owner()
async def sync(
  ctx: Context, guilds: Greedy[discord.Object], spec: Optional[Literal["~", "*", "^"]] = None) -> None:
    if not guilds:
        if spec == "~":
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "*":
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
        elif spec == "^":
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            synced = []
        else:
            synced = await ctx.bot.tree.sync()
        if debug:
            print(f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}")
        await ctx.send(
            f"Synced {len(synced)} commands {'globally' if spec is None else 'to the current guild.'}"
        )
        return

    ret = 0
    for guild in guilds:
        try:
            await ctx.bot.tree.sync(guild=guild)
        except discord.HTTPException:
            pass
        else:
            ret += 1

    await ctx.send(f"Synced the tree to {ret}/{len(guilds)}.")

@tasks.loop(seconds=30)
async def check_version():
    await auto_update_git.check_version(bot, send_developer_message)

@check_version.before_loop
async def before_check_version():
    initial_delay = get_initial_delay(interval=timedelta(seconds=30))
    print('Version Check loop scheduled for: {}'.format(initial_delay))
    await asyncio.sleep(initial_delay)

async def run_bot():
    while True:
        try:
            await bot.start(_secrets.DISCORD_TOKEN)  # Replace TOKEN with your bot token
        except (discord.ConnectionClosed, discord.GatewayNotFound, discord.HTTPException) as exc:
            print(f"Connection error occurred: {exc}, trying to reconnect...")

            # Wait for bot to be ready with a timeout
            try:
                await asyncio.wait_for(bot.wait_until_ready(), timeout=60)
            except asyncio.TimeoutError:
                print("Reconnect failed, restarting the bot...")
                await bot.close()
        except discord.errors.LoginFailure:
            print(
                "An improper token was provided. Please check your token and try again.")
            await bot.close()
        except KeyboardInterrupt:
            await bot.close()
            break
        except Exception as exc:
            print(f"An unexpected error occurred: {exc}")
            await bot.close()
            break

if __name__ == "__main__":
    asyncio.run(run_bot())
