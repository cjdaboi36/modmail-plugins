import discord
from discord.ext import commands

class RoleMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.required_role = None

    @commands.command(name='setrole')
    @commands.has_permissions(administrator=True)
    async def set_role(self, ctx, *, role: discord.Role):
        """Sets the required role for ticket check."""
        self.required_role = role.id
        await ctx.send(f"✅ Required role has been set to: {role.name}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.name.startswith("ticket-"):
            if self.required_role is not None:
                user_roles = [role.id for role in message.author.roles]
                if self.required_role not in user_roles:
                    await message.channel.send(f"🚫 {message.author.mention} does not have the required role to open a ticket.")

    @commands.command(name='checkrole')
    async def check_role(self, ctx):
        """Displays the currently set required role."""
        if self.required_role:
            role = discord.utils.get(ctx.guild.roles, id=self.required_role)
            await ctx.send(f"📋 The required role is currently set to: {role.name}")
        else:
            await ctx.send("⚠️ No role has been set yet.")

async def setup(bot):
    await bot.add_cog(RoleMessage(bot))