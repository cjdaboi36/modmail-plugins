import discord
from discord.ext import commands

class Hi(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='hi')
    async def hi(self, ctx):
        """Sends an embed with an emoji saying Hello!"""
        
        embed = discord.Embed(
            title="👋 Hello!",
            description="Hi there! I'm a bot saying hello with an emoji!",
            color=discord.Color.blue()
        )

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Hi(bot))