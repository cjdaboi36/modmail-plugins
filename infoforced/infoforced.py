import discord
from discord.ext import commands
from core import checks, utils
from core.models import PermissionLevel, getLogger

logger = getLogger(__name__)


class Wantuh(commands.Cog):

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
            url="https://discord.gg/F34cRU8",
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        desc = "This is an open source Discord bot that serves as a means for "
        desc += "members to easily receive support by administartors. "
        embed.description = desc

        embed.add_field(name="Uptime", value=self.bot.uptime)
        embed.add_field(name="Latency", value=f"{self.bot.latency * 1000:.2f} ms")
        embed.add_field(name="Version", value=f"`{self.bot.version}`")
        embed.add_field(name="Authors", value="`kyb3r`, `Taki`, `fourjr`")
        embed.add_field(name="Hosting Method", value="`WANTUH`")



        embed.add_field(
            name="Wantuh's Hosting Service",
            value=f"Wantuh's Hosting Service is a service ran by <@561312593155981323>, if you wish "
            "to have a Modmail bot of your own please contact him. Join https://discord.gg/Xyrb2j8FP2 or Email helpdesk@wantuh.com for any support or questions.",
            inline=False,
        )

        embed.add_field(
            name="Modmail",
            value="Open source bot on [GitHub](https://github.com/khakers/OpenModmail/tree/oldstable), stable version "
            "by <@184473972446986240> (khakers)",
            inline=False,

        )

        footer = "Wantuh's Hosting Service"
        embed.set_footer(text=footer)
        await ctx.send(embed=embed)

async def setup(bot):
    result = bot.remove_command("about")
    if result is None:
        logger.error("Failed to remove 'about' command. Something has probably gone wrong.")
    await bot.add_cog(Foo(bot))
