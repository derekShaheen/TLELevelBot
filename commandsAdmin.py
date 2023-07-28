from discord.ext import commands
import discord
from configManager import load_guild_data, save_guild_data, load_user_data, save_user_data
from levelSystem import calculate_level, adjust_roles
from util import send_embed

@commands.command(
    brief='Set the level of a specific user.',  # Short description of command
    help='Set the level of a specific user. This command requires administrator permissions.',  # Detailed description
)
@commands.has_permissions(administrator=True)
async def set_level(ctx, member: discord.Member, level: int):
    # Load user data
    user_data = load_user_data(ctx.guild.id, member.id)
    
    # Save old level
    old_level = user_data['level']
    
    # Calculate the experience needed for the target level
    experience = 0
    for i in range(level - 1):
        experience += (i + 1) * 2
    
    # Set the user's level and experience
    user_data['level'] = level
    user_data['experience'] = experience
    
    # Save user data
    save_user_data(ctx.guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(ctx.guild, old_level, level, member)
    
    await ctx.send(f"{member.name}'s level has been set to {level}.")


@commands.command(
    brief='Adjust the experience of a specific user.',  # Short description of command
    help='Adjust the experience of a specific user. This command requires administrator permissions.',  # Detailed description
)
@commands.has_permissions(administrator=True)

async def xp(ctx, member: discord.Member, experience: int):
    # Load user data
    user_data = load_user_data(ctx.guild.id, member.id)
    
    # Old level
    old_level = user_data['level']
    
    # Adjust the experience in the user's total
    user_data['experience'] += experience
    if user_data['experience'] < 0:
        user_data['experience'] = 0

    # Calculate new level
    new_level = calculate_level(user_data['experience'])
    user_data['level'] = new_level

    # Save user data
    save_user_data(ctx.guild.id, member.id, user_data)

    # Adjust roles
    await adjust_roles(ctx.guild, old_level, new_level, member)
    
    # Send an embed message for leveling up or down
    embed = discord.Embed(
        title=f"{member.name}, your level has changed!", 
        description=f"You are now level {new_level}!", 
        color=0x00ff00 if new_level >= old_level else 0xff0000
    )
    await ctx.send(embed=embed)
    
    await ctx.send(f"{abs(experience)} experience points have been {'added to' if experience >= 0 else 'removed from'} {member.name}'s total.")


@commands.command(
    brief='Set a role for a specific level.',  # Short description of command
    help='Set a role for a specific level. This command requires administrator permissions.',  # Detailed description
)
@commands.has_permissions(administrator=True)
async def set_level_role(ctx, level: int, *, role: discord.Role):
    # Load guild data
    guild_data = load_guild_data(ctx.guild.id)
    
    # Add the level-role mapping
    if 'level_roles' not in guild_data:
        guild_data['level_roles'] = {}
    guild_data['level_roles'][str(level)] = role.id
    
    # Save guild data
    save_guild_data(ctx.guild.id, guild_data)
    
    await ctx.send(f"The role for level {level} has been set to {role.name}.")

@commands.command(
    name='set_channel',
    brief='Set a specific channel for certain notifications.',  # Short description of command
    help='Set a specific channel for announcements or the leaderboard. Valid channel types are "leaderboard" or "publog". This command requires administrator permissions.'  # Detailed description
)
@commands.has_permissions(administrator=True)
async def set_channel(ctx, channel_type: str, *, channel_name: str):
    guild_id = ctx.guild.id
    guild_data = load_guild_data(guild_id)
    
    if channel_type.lower() not in ['leaderboard', 'publog']:
        await ctx.send('Invalid channel type. Please specify either "leaderboard" or "publog".')
        return

    # Get the channel by its name
    channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if not channel:
        await ctx.send(f"Couldn't find a channel named {channel_name}.")
        return

    # Update the guild data
    guild_data[channel_type.lower()] = channel.id
    save_guild_data(guild_id, guild_data)

    await ctx.send(f"Set the {channel_type} channel to {channel_name}.")

@commands.command(name='blacklist', help='Toggle blacklist status for a user')
@commands.has_permissions(administrator=True)
async def toggle_blacklist(ctx, user: discord.Member):
    user_data = load_user_data(ctx.guild.id, user.id)
    # Toggle the blacklist status
    user_data['blacklisted'] = not user_data.get('blacklisted', False)
    save_user_data(ctx.guild.id, user.id, user_data)
    # Reply with the new status
    if user_data['blacklisted']:
        await ctx.send(f"{user.name} has been added to the blacklist.")
    else:
        await ctx.send(f"{user.name} has been removed from the blacklist.")