from discord.ext import commands
import discord
from configManager import load_user_data

@commands.command(
    brief='Displays the level and experience of a user.',  # Short description of command
    help='Displays the level and experience of a user. If no user is mentioned, it will display the level of the command user.',  # Detailed description
    aliases=['lvl']  # Alternative ways to call the command
)
async def level(ctx, member: discord.Member = None):
    # If no member is mentioned, show the level of the command user
    if not member:
        member = ctx.author
    
    # Load user data
    user_data = load_user_data(ctx.guild.id, member.id)
    
    # Create an embed message
    embed = discord.Embed(title=f"{member.name}'s level", description=f"Level: {user_data['level']}\nExperience: {user_data['experience']}", color=0x00ff00)
    await ctx.send(embed=embed)

# @commands.command()
# async def leaderboard(ctx):
#     # Load all user data for the guild
#     user_data_list = []
#     for member in ctx.guild.members:
#         user_data = load_user_data(ctx.guild.id, member.id)
#         user_data_list.append((member, user_data['experience'], user_data['level']))
    
#     # Sort by experience in descending order
#     user_data_list.sort(key=lambda x: x[1], reverse=True)
    
#     # Create an embed message
#     embed = discord.Embed(title=f"Leaderboard for {ctx.guild.name}", color=0x00ff00)
#     for i, (member, experience, level) in enumerate(user_data_list[:10], start=1):
#         embed.add_field(name=f"#{i} {member.name}", value=f"Level: {level}\nExperience: {experience}", inline=False)
#     await ctx.send(embed=embed)
