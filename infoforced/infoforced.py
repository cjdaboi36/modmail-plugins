import discord
from discord.ext import commands
from core import checks, utils
from core.models import PermissionLevel, getLogger

logger = getLogger(__name__)


class Foo(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=["info"])
    @checks.has_permissions(PermissionLevel.REGULAR)
    @utils.trigger_typing
    async def about(self, ctx):
        """Shows information about this bot."""
        embed = discord.Embed(color=self.bot.main_color, timestamp=discord.utils.utcnow())
        embed.set_author(
            name="Modmail - Information",
            icon_url=self.bot.user.display_avatar.url,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        desc = "This is an open source Discord bot that serves as a means for "
        desc += "members to easily receive support by administartors. "
        embed.description = desc

        embed.add_field(name="Uptime", value=self.bot.uptime)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f} ms")
        embed.add_field(name="Version", value=f"`{self.bot.version}`")
        embed.add_field(name="Authors", value="`kyb3r`, `Taki`, `fourjr`")
        embed.add_field(name="Hosting Method", value="`CJSCOMMISIONS`")



        embed.add_field(
            name="Cj's Commisions Modmail Hosting",
            value=f"Cj's Commisions Modmail Hosting"
            "To get a modmail bot hosted by us join https://discord.gg/F9yPkvcTzY.",
            inline=False,

        footer = "Cj's Commisions Hosting Service"
        embed.set_footer(text=footer)
        await ctx.send(embed=embed)

async def setup(bot):
    result = bot.remove_command("about")
    if result is None:
        logger.error("Failed to remove 'about' command. Something has probably gone wrong.")
    await bot.add_cog(Foo(bot))
