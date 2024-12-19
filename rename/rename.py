import discord
from discord.ext import commands

from core import checks
from core.models import PermissionLevel

import datetime

class Rename(commands.Cog):
    """Rename a thread automatically!"""

    def __init__(self, bot):
        self.bot = bot

    @checks.thread_only()
    @checks.has_permissions(PermissionLevel.SUPPORTER)
    @commands.command()
    async def rename(self, ctx):
        try:
            # Add reaction to indicate the process is starting
            await ctx.message.add_reaction('⏰')

            # Get the username of the user who ran the command
            user_who_ran_command = ctx.author.name

            # Get the current channel name, which contains the ticket owner's username
            current_channel_name = ctx.channel.name

            # Format the new channel name
            new_channel_name = f"{user_who_ran_command}-{current_channel_name}"

            # Edit the channel name
            await ctx.channel.edit(name=new_channel_name)

            # Clear the loading reaction and add a success reaction
            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('✅')
        except discord.errors.Forbidden:
            embed = discord.Embed(
                title='Forbidden',
                description="Uh oh, it seems I can't perform this action due to my permission levels.",
                color=discord.Color.red()
            )
            embed.timestamp = datetime.datetime.utcnow()
            embed.set_footer(text='Rename')

            await ctx.reply(embed=embed)

            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('❌')
        except Exception as e:
            # Log the error if needed (optional)
            print(f"Error during rename: {e}")

            await ctx.message.clear_reactions()
            await ctx.message.add_reaction('❌')

async def setup(bot):
    await bot.add_cog(Rename(bot))
