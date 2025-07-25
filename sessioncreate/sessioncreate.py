import discord
from discord.ext import commands
import aiohttp
import os
# from types import SimpleNamespace # No longer strictly needed if using DummyMessage
from core.thread import Thread # Import the Thread class
from core.models import DummyMessage # <--- IMPORTANT: Import DummyMessage

class LogSession(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Prefer environment variable for Docker deployments (CDN_API_KEY from .env via docker-compose)
        self.api_key = os.getenv('CDN_API_KEY')
        
        if not self.api_key:
            # Fallback to config.ini if environment variable not set (less common for Docker, but good for flexibility)
            self.api_key = self.bot.config.get('api_keys', 'CDN_API_KEY', fallback=None) 
            if not self.api_key:
                print("ERROR: CDN_API_KEY is not configured via environment variable or config.ini for LogSession cog. Commands might fail.")

    @commands.command(name='createsession', aliases=['cs', 'newlogsession'])
    @commands.has_permissions(manage_channels=True) # Only allow users who can manage channels (staff)
    async def create_session_command(self, ctx):
        """
        Generates a new log upload session and sends links to the ticket.
        Usage: .createsession
        """
        if not self.api_key:
            # Staff-facing error, no need to relay to user
            return await ctx.send("Error: CDN API Key is not configured for this command. Please contact the bot administrator.")

        # --- CRITICAL FIX: Use Thread.from_channel to get the ticket object ---
        try:
            ticket = await Thread.from_channel(self.bot.threads, ctx.channel)
        except ValueError: # from_channel can raise ValueError if topic is malformed etc.
            return await ctx.send("This command can only be used in a valid Modmail ticket channel.")
        
        if not ticket: # Although from_channel should always return a Thread if successful, this is a good safety check
            return await ctx.send("Could not retrieve ticket information from this channel.")
        # ---------------------------------------------------------------------

        # Send an initial message to the staff channel to show the bot is processing
        # This message is not relayed to the user.
        processing_message = await ctx.send("Generating a new log upload session, please wait...")

        api_endpoint = 'https://cdn.avionicsrblx.com/api/logs/generate' # Your CDN server endpoint

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_endpoint,
                    headers={
                        'api-key': self.api_key, # Use the API key from your config
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    # --- Robust deletion for processing_message ---
                    try:
                        await processing_message.delete()
                    except discord.NotFound:
                        print("Warning: Processing message already deleted or not found.")
                    # ---------------------------------------------

                    if response.status != 200:
                        error_data = await response.json(content_type=None) # Handle potential non-JSON errors
                        error_message = error_data.get('error', f'Unknown error. Status: {response.status}')
                        print(f"API Error from CDN server ({response.status}): {error_message}")
                        # Staff-facing error
                        return await ctx.send(f"Error from CDN server: {error_message[:250]}...") # Truncate for Discord

                    data = await response.json()

                    if data.get('success'):
                        upload_link = data.get('uploadLink')
                        view_link = data.get('viewLink')
                        session_id = data.get('sessionId', 'N/A')

                        # Construct the message content for the Modmail reply via the ticket object
                        # This message WILL be relayed to the user's DM.
                        message_to_send_to_user = f"Here is your upload link: {upload_link}"

                        # --- Create a DummyMessage object for the ticket.reply() method ---
                        dummy_message = DummyMessage() # Instantiate DummyMessage
                        dummy_message.content = message_to_send_to_user
                        dummy_message.author = ctx.author # The author of the command (staff)
                        dummy_message.attachments = []
                        dummy_message.embeds = []
                        dummy_message.components = [] # Explicitly clear
                        dummy_message.stickers = []   # Explicitly clear

                        # Call ticket.reply - this sends the message to the user's DM and staff channel
                        staff_msgs, user_msgs = await ticket.reply(dummy_message)

                        if user_msgs:
                            print(f"Successfully sent log session link to user's DM: {user_msgs[0].id}")
                        else:
                            print("Warning: User message not found in ticket.reply response. Check Modmail settings.")
                        # ----------------------------------------------------------------

                        # Create and send the embed for the staff view link.
                        # This embed is for staff eyes only and is NOT relayed to the user's DM.
                        view_embed = discord.Embed(
                            title="Staff View Link for Session",
                            description="Staff can use this link to view the uploaded images.",
                            color=discord.Color.green(), # Green color for success
                            timestamp=discord.utils.utcnow() # Current UTC time
                        )
                        view_embed.add_field(name="Staff View Link", value=f"[Click Here]({view_link})", inline=False)
                        view_embed.set_footer(text=f"Session ID: {session_id}")
                        
                        await ctx.send(embed=view_embed) # Send to staff channel only

                        print(f"Log session created by {ctx.author} in ticket {ctx.channel.id} (Session ID: {session_id})")

                    else:
                        await ctx.send(f"Failed to create session: {data.get('error', 'Unknown error from server.')}") # Staff-facing error

        except aiohttp.ClientError as e:
            # --- Robust deletion for processing_message in error handling ---
            try:
                await processing_message.delete()
            except discord.NotFound:
                pass # Already handled or not found, proceed with error message
            # --------------------------------------------------------------
            await ctx.send(f"Network error communicating with CDN server: `{e}`. Please ensure the server is running.") # Staff-facing error
        except Exception as e:
            # --- Robust deletion for processing_message in error handling ---
            try:
                await processing_message.delete()
            except discord.NotFound:
                pass # Already handled or not found, proceed with error message
            # --------------------------------------------------------------
            await ctx.send(f"An unexpected error occurred: `{e}`. Please check bot logs.") # Staff-facing error
            print(f"Unexpected error in create_session_command: {e}")

async def setup(bot):
    """Adds the LogSession cog to the bot."""
    await bot.add_cog(LogSession(bot))