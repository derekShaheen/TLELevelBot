from util import verify_libraries_installed

libraries = [
    ("discord", "discord.py"),
    ("asyncio", "asyncio"),
    ("yaml", "PyYAML"),
    ("asciichartpy", "asciichartpy"),
    ("pandas", "pandas"),
    ("pytz", "pytz"),
    ("requests", "requests"),
    ("pprint", "pprint"),
    ("matplotlib", "matplotlib")
]

verify_libraries_installed(libraries)

import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from discord.ext.commands import Greedy, Context
from typing import Literal, Optional

import pprint
import _secrets
from configManager import load_user_data, load_config, save_user_data, load_guild_data, save_guild_data, load_all_user_data
from levelSystem import process_experience, generate_leaderboard, log_level_up, cumulative_experience_for_level, generate_leaderboard_image
from util import get_initial_delay, get_random_color
from debug_logger import DebugLogger
import auto_update_git

debug = True

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, reconnect=True)
debug_logger = DebugLogger.get_instance(bot)
config = load_config()

# Import commands after 'bot' has been initialized
import commandsAdmin
import commandsUser

@bot.event
async def on_ready():
    if debug:
        debug_logger.start()

    debug_logger.log(f"Configuration: ```{pprint.pformat(config)}```")

    # Pre-calculate the experience for 100 levels so it can be referenced in memory later
    debug_logger.log(f"Pre-calculating experience for 100 levels...")
    cumulative_experience_for_level(100)

    # Load guild data for each guild the bot is in
    for guild in bot.guilds:
        guild_data = load_guild_data(guild.id)
        # Remove 'levelup_log' from data for logging
        guild_data_for_logging = {k: v for k, v in guild_data.items() if k != 'levelup_log'}
        debug_logger.log(f"Guild {guild.name} data: ```{pprint.pformat(guild_data_for_logging)}```")

        # Update the level up log message
        await log_level_up(bot, guild, None, 0)
        
        # Process initial experience/roles for each user data in the guild
        debug_logger.log(f"Processing initial experience/roles for guild {guild.name}...")
        user_data_list = load_all_user_data(guild.id)
        for user_id, user_data in user_data_list:
            # Note: The user_id should be converted to an integer
            member = guild.get_member(int(user_id))
            if member:  # Make sure the member still exists in the guild
                await process_experience(bot, guild, member, debug, 'on_ready')
            #else: 
                #username = user_data.get('username') or "UNKNOWN"
                #debug_logger.log(f"User {user_id} [{username}] not found in guild {guild.name}, skipping...")
        debug_logger.log(f"Processing complete.")


    voice_activity_tracker.start()
    update_leaderboard_task.start()

    check_version.start()
    
#    await update_leaderboard()
#    await check_version()

@tasks.loop(minutes=1)
async def voice_activity_tracker():
    if debug:
        debug_logger.log(f"Updating credits")

    for guild in bot.guilds:
        for member in guild.members:
            await process_experience(bot, guild, member, debug, 'voice_activity')

    if debug:
        debug_logger.log(f"Credit update complete.")

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

    # Load or initialize user data
    user_data = load_user_data(message.guild.id, message.author.id)

    now = datetime.now()
    
    # Handle chat timestamp tracking
    # Initialize 'chats_timestamps' if it doesn't exist
    if 'chats_timestamps' not in user_data:
        user_data['chats_timestamps'] = []

    # Remove timestamps older than 3 minutes
    user_data['chats_timestamps'] = [timestamp for timestamp in user_data['chats_timestamps'] if now - timestamp < timedelta(minutes=3)]

    # Add new timestamp
    user_data['chats_timestamps'].append(now)

    # Save user data after updating it
    save_user_data(message.guild.id, message.author.id, user_data)
    # End chat timestamp tracking
    await process_experience(bot, message.guild, message.author, debug, 'chat', message)

    # Process commands after checking for spam and awarding points
    await bot.process_commands(message)

@tasks.loop(minutes=60)
async def update_leaderboard_task():
    await update_leaderboard()

async def update_leaderboard():
    debug_logger.log(f"Updating leaderboard...")

    for guild in bot.guilds:
        guild_data = load_guild_data(guild.id)
        leaderboard_channel_id = guild_data.get('leaderboard')
        leaderboard_channel = bot.get_channel(leaderboard_channel_id) if leaderboard_channel_id else None

        await clear_channel_except(guild.id, leaderboard_channel_id)

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
        debug_logger.log(f"Update complete.")
        auto_update_git.backup_to_github()

@update_leaderboard_task.before_loop
async def before_update_leaderboard_task():
    initial_delay = get_initial_delay(interval=timedelta(hours=1, seconds=5))
    if debug:
        print('Update leaderboard scheduled for: {}'.format(initial_delay))
    await asyncio.sleep(initial_delay)

async def clear_channel_except(guild_id: int, channel_id: int):
    keep_message_ids = []
    guild_data = load_guild_data(guild_id)
    channel = bot.get_channel(channel_id)

    if not channel:
        print(f"Channel {channel_id} not found")
        return
    
    keep_message_ids.append(guild_data.get('leaderboard_message'))
    keep_message_ids.append(guild_data.get('levelup_log_message'))

    async for message in channel.history():
        if message.id not in keep_message_ids:
            try:
                await message.delete()
            except discord.NotFound:
                pass  # Message already deleted, move on to next message
            except discord.HTTPException as e:
                print(f"Failed to delete message {message.id}: {e}")
            await asyncio.sleep(0.5)  # To respect the rate limit

@bot.tree.command(
    name='update_leaderboard',
    description='Admin only command. Update the leaderboard.',
)
# @app_commands.choices(choices=[
#     app_commands.Choice(name="Full Board", value=1),
#     app_commands.Choice(name="Default", value=0),
# ])
@app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
@app_commands.checks.has_permissions(administrator=True)
#async def update_leaderboard_command(interaction: discord.Interaction, choices: app_commands.Choice[int]):
async def update_leaderboard_command(interaction: discord.Interaction):
    await interaction.response.defer()  # Acknowledge the command, but don't send a response yet
    # if choices.value == 1:  # If Full Board is chosen
    #     leaderboard = await generate_leaderboard(bot, interaction.guild_id, True)
    #     await interaction.followup.send(f"```{leaderboard}```")  # Send the full leaderboard as a response

    #else:  # If Default is chosen
    await update_leaderboard()  # Update the leaderboard
    await interaction.followup.send("Leaderboard has been updated!")  # Send a response after the leaderboard has been updated

@bot.tree.command(
    name='view_leaderboard',
    description='Admin only command. View the full leaderboard.',
)
@app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
@app_commands.checks.has_permissions(administrator=True)
async def update_leaderboard_command(interaction: discord.Interaction):
    await interaction.response.defer()  # Acknowledge the command, but don't send a response yet

    image_path = await generate_leaderboard_image(bot, interaction.guild_id, True)
    embed = discord.Embed(title="Leaderboard")
    embed.set_image(url="attachment://leaderboard.png")
    await interaction.followup.send(file=discord.File(image_path), embed=embed)
    
#------ Sync Tree ------
guild = discord.Object(id='262726474967023619')
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
    await auto_update_git.check_version(bot)

@check_version.before_loop
async def before_check_version():
    auto_update_git.set_initial_run_sha()
    await auto_update_git.check_version(bot) # Perform initial check
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
