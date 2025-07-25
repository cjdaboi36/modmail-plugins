import discord
from discord.ext import commands
import aiohttp
import os

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
            return await ctx.send("Error: CDN API Key is not configured for this command. Please contact the bot administrator.")

        # Send an initial message to show the bot is processing
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
                    # Delete the "processing" message after we get a response
                    await processing_message.delete()

                    if response.status != 200:
                        error_data = await response.json(content_type=None) # Handle potential non-JSON errors
                        error_message = error_data.get('error', f'Unknown error. Status: {response.status}')
                        print(f"API Error from CDN server ({response.status}): {error_message}")
                        return await ctx.send(f"Error from CDN server: {error_message[:250]}...") # Truncate for Discord

                    data = await response.json()

                    if data.get('success'):
                        upload_link = data.get('uploadLink')
                        view_link = data.get('viewLink')
                        session_id = data.get('sessionId', 'N/A')

                        # Send the plain text upload link as a separate message
                        await ctx.send(f"Here is your upload link: {upload_link}")

                        # Create and send the embed for the staff view link
                        view_embed = discord.Embed(
                            title="Staff View Link for Session",
                            description="Staff can use this link to view the uploaded images.",
                            color=discord.Color.green(), # Green color for success
                            timestamp=discord.utils.utcnow() # Current UTC time
                        )
                        view_embed.add_field(name="Staff View Link", value=f"[Click Here]({view_link})", inline=False)
                        view_embed.set_footer(text=f"Session ID: {session_id}")
                        
                        # If you have a URL for an upload icon, you could add it here
                        # For example: view_embed.set_thumbnail(url="https://example.com/upload_icon.png")

                        await ctx.send(embed=view_embed)

                        # You can add a logging call here if OpenModmail has a specific logging function for commands
                        print(f"Log session created by {ctx.author} in ticket {ctx.channel.id} (Session ID: {session_id})")

                    else:
                        await ctx.send(f"Failed to create session: {data.get('error', 'Unknown error from server.')}")

        except aiohttp.ClientError as e:
            # Ensure processing message is deleted even on network errors
            if processing_message and processing_message.id: # Check if message exists to delete
                await processing_message.delete()
            await ctx.send(f"Network error communicating with CDN server: `{e}`. Please ensure the server is running.")
        except Exception as e:
            # Ensure processing message is deleted even on other errors
            if processing_message and processing_message.id:
                await processing_message.delete()
            await ctx.send(f"An unexpected error occurred: `{e}`. Please check bot logs.")
            print(f"Unexpected error in create_session_command: {e}")

async def setup(bot):
    """Adds the LogSession cog to the bot."""
    await bot.add_cog(LogSession(bot))