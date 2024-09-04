import discord
from discord.ext import commands

class RoleMessage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.required_role = None
        self.main_guild_id = None

    @commands.command(name='setrole')
    @commands.has_permissions(administrator=True)
    async def set_role(self, ctx, *, role: discord.Role):
        """Sets the required role for ticket check."""
        self.required_role = role.id
        await ctx.send(f"✅ Required role has been set to: {role.name}")

    @commands.command(name='setmainguild')
    @commands.has_permissions(administrator=True)
    async def set_main_guild(self, ctx, guild_id: int):
        """Sets the main guild (server) where the user's roles will be checked."""
        self.main_guild_id = guild_id
        await ctx.send(f"✅ Main server has been set to guild ID: {guild_id}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.name.startswith("ticket-"):
            if self.required_role is not None and self.main_guild_id is not None:
                main_guild = self.bot.get_guild(self.main_guild_id)
                if not main_guild:
                    await message.channel.send("⚠️ Main server not found. Please ensure the correct server ID is set.")
                    return
                
                try:
                    main_member = await main_guild.fetch_member(message.author.id)
                except discord.errors.NotFound:
                    await message.channel.send(f"🚫 {message.author.mention} is not a member of the main server.")
                    return

                user_roles = [role.id for role in main_member.roles]
                if self.required_role not in user_roles:
                    await message.channel.send(f"🚫 {message.author.mention} does not have the required role in the main server.")
    
    @commands.command(name='checkrole')
    async def check_role(self, ctx):
        """Displays the currently set required role and main guild."""
        if self.required_role:
            role = discord.utils.get(ctx.guild.roles, id=self.required_role)
            role_name = role.name if role else "Role not found"
            main_guild = self.bot.get_guild(self.main_guild_id)
            guild_name = main_guild.name if main_guild else "Guild not found"
            await ctx.send(f"📋 Required role: {role_name}\n🌍 Main server: {guild_name}")
        else:
            await ctx.send("⚠️ No role or main server has been set yet.")

async def setup(bot):
    await bot.add_cog(RoleMessage(bot))