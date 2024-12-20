import discord
from discord.ext import commands
from pymongo import MongoClient
from core.models import PermissionLevel
from core import checks

import os

class CheckRole(commands.Cog):
    """Check roles for ticket holders and display them when opening a ticket."""

    def __init__(self, bot):
        self.bot = bot

        # Initialize MongoDB connection
        mongo_uri = os.getenv("MONGO_URI")
        self.client = MongoClient(mongo_uri)
        self.db = self.client["modmail_bot"]  # Replace "modmail" with your database name if different
        self.role_collection = self.db["roles"]

    @commands.Cog.listener()
    async def on_thread_create(self, thread, creator):
        """Triggered when a new thread is created."""
        guild = self.bot.get_guild(int(os.getenv("GUILD_ID")))
        if not guild:
            return

        # Get the member object for the user who created the thread
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
            color=discord.Color.blue()
        )

        for role_name, has_role in role_status.items():
            embed.add_field(
                name=role_name,
                value="✅ Has Role" if has_role else "❌ Does Not Have Role",
                inline=False
            )

        # Send the embed to the thread
        await thread.send(embed=embed)

    @checks.has_permissions(PermissionLevel.ADMIN)
    @commands.command()
    async def addrole(self, ctx, role: discord.Role):
        """Add a role to the role check list."""
        self.role_collection.update_one(
            {"role_id": role.id},
            {"$set": {"role_id": role.id, "role_name": role.name}},
            upsert=True
        )
        await ctx.send(f"Role `{role.name}` has been added to the role check list.")

    @checks.has_permissions(PermissionLevel.ADMIN)
    @commands.command()
    async def removerole(self, ctx, role: discord.Role):
        """Remove a role from the role check list."""
        self.role_collection.delete_one({"role_id": role.id})
        await ctx.send(f"Role `{role.name}` has been removed from the role check list.")

async def setup(bot):
    await bot.add_cog(CheckRole(bot))
