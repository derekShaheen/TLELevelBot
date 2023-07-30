from discord.ext import commands
import discord
from configManager import load_user_data, save_user_data
from util import send_embed, get_random_color
from datetime import datetime, timedelta
from discord import app_commands
from __main__ import bot

def check_command_cooldown(user_data, command_key, cooldown_minutes):
    # Check if the last use was less than cooldown_minutes ago
    now = datetime.now()
    last_used = user_data.get(command_key)
    if last_used and now - last_used < timedelta(minutes=cooldown_minutes):
        return False  # The command is still cooling down
    else:
        user_data[command_key] = now
        return True  # The command is not cooling down and can be used

# Create the context menu command that only works on members
@bot.tree.context_menu(name='Show Reputation')
async def show_rep(interaction: discord.Interaction, member: discord.Member):
    await show_rep_util(interaction, member)

# Create the slash command
@bot.tree.command(description='Show Reputation for yourself or another member.')
@app_commands.guild_only()
@app_commands.checks.cooldown(1, 5.0, key=lambda i: (i.guild_id, i.user.id))
@app_commands.describe(member='The member you want to check the reputation for...')
async def rep(interaction: discord.Interaction, member: discord.Member = None):
    # If no member is mentioned, show the rep of the command user
    if not member:
        member = interaction.user

    # Run the same code as the context menu command
    await show_rep_util(interaction, member)

async def show_rep_util(interaction: discord.Interaction, member: discord.Member):
    # Load user data
    user_data = load_user_data(interaction.guild.id, member.id)

    # Capitalize the first letter of the username
    username = member.name[0].upper() + member.name[1:]

    # Approximate the experience to the nearest 100 if it's more than 100
    experience = user_data['experience']
    if experience > 100:
        experience = round(experience / 100) * 100

    # Create an embed
    embed = discord.Embed(
        title=f"{username}'s Reputation Information",
        description='',
        color=get_random_color()
    )

    avatar_url = str(member.avatar.url) if member.avatar else str(member.default_avatar.url)
    embed.set_thumbnail(url=avatar_url)

    # Add fields to the embed
    embed.add_field(name="Level", value=user_data['level'], inline=True)
    embed.add_field(name="Approx Reputation", value=experience, inline=True)  # Use the approximated experience

    # Send the embed with the interaction response
    await interaction.response.send_message(embed=embed)
