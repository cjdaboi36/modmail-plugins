import os
import discord
from discord.ext import commands
from pymongo import MongoClient
from core import checks
from core.models import PermissionLevel


class CheckRole(commands.Cog):
    """A plugin to check a user's roles when a ticket is opened."""

    def __init__(self, bot):
        self.bot = bot

        # Connect to MongoDB
        mongo_uri = os.getenv("MONGO_URI")
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client["modmail_bot"]
        self.role_collection = self.db["roles"]

    @checks.has_permissions(PermissionLevel.ADMIN)
    @commands.group(name="checkrole", invoke_without_command=True)
    async def checkrole(self, ctx):
        """Base command for managing roles in the role-check system."""
        await ctx.send_help(ctx.command)

    @checks.has_permissions(PermissionLevel.ADMIN)
    @checkrole.command(name="addrole")
    async def addrole(self, ctx, role: discord.Role):
        """Add a role to the role-check system."""
        existing_role = self.role_collection.find_one({"role_id": role.id})

        if existing_role:
            await ctx.send(f"The role `{role.name}` is already in the system.")
            return

        self.role_collection.insert_one({"role_id": role.id, "role_name": role.name})
        await ctx.send(f"Role `{role.name}` has been added to the role-check system.")

    @checks.has_permissions(PermissionLevel.ADMIN)
    @checkrole.command(name="removerole")
    async def removerole(self, ctx, role: discord.Role):
        """Remove a role from the role-check system."""
        result = self.role_collection.delete_one({"role_id": role.id})

        if result.deleted_count == 0:
            await ctx.send(f"The role `{role.name}` is not in the system.")
            return

        await ctx.send(f"Role `{role.name}` has been removed from the role-check system.")

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Triggered when a new thread is created."""
        guild = self.bot.get_guild(int(os.getenv("GUILD_ID")))
        if not guild:
            return

        # Get the first message to determine the thread creator
        async for message in thread.history(limit=1, oldest_first=True):
            creator = message.author

        # Ensure the creator is a member of the guild
        member = guild.get_member(creator.id)
        if not member:
            return

        # Retrieve roles from MongoDB
        stored_roles = self.role_collection.find()
        role_status = {}

        # Check if the user has the required roles
        for role_data in stored_roles:
            role_id = role_data["role_id"]
            role_name = role_data["role_name"]
            has_role = discord.utils.get(member.roles, id=role_id) is not None
            role_status[role_name] = has_role

        # Build the embed to display role statuses
        embed = discord.Embed(
            title=f"Role Check for {member.display_name}",
            description="Here are the roles you have and don't have:",
            color=discord.Color.blue(),
        )

        for role_name, has_role in role_status.items():
            embed.add_field(
                name=role_name,
                value="✅ Has Role" if has_role else "❌ Does Not Have Role",
                inline=False,
            )

        # Send the embed to the thread
        await thread.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CheckRole(bot))
