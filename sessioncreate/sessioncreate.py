import discord
from discord.ext import commands
import aiohttp
import os
from types import SimpleNamespace # <-- Import SimpleNamespace to create a dummy message object

class LogSession(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('CDN_API_KEY')
        
        if not self.api_key:
            self.api_key = self.bot.config.get('api_keys', 'CDN_API_KEY', fallback=None) 
            if not self.api_key:
                print("ERROR: CDN_API_KEY is not configured via environment variable or config.ini for LogSession cog. Commands might fail.")

    @commands.command(name='createsession', aliases=['cs', 'newlogsession'])
    @commands.has_permissions(manage_channels=True) 
    async def create_session_command(self, ctx):
        if not self.api_key:
            return await ctx.send("Error: CDN API Key is not configured for this command. Please contact the bot administrator.")

        ticket = self.bot.get_ticket(ctx.channel.id)
        if not ticket:
            return await ctx.send("This command can only be used in a Modmail ticket channel.")

        processing_message = await ctx.send("Generating a new log upload session, please wait...")

        api_endpoint = 'https://cdn.avionicsrblx.com/api/logs/generate' 

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    api_endpoint,
                    headers={
                        'api-key': self.api_key, 
                        'Content-Type': 'application/json'
                    }
                ) as response:
                    try:
                        await processing_message.delete()
                    except discord.NotFound:
                        print("Warning: Processing message already deleted or not found.")

                    if response.status != 200:
                        error_data = await response.json(content_type=None) 
                        error_message = error_data.get('error', f'Unknown error. Status: {response.status}')
                        print(f"API Error from CDN server ({response.status}): {error_message}")
                        return await ctx.send(f"Error from CDN server: {error_message[:250]}...")

                    data = await response.json()

                    if data.get('success'):
                        upload_link = data.get('uploadLink')
                        view_link = data.get('viewLink')
                        session_id = data.get('sessionId', 'N/A')

                        message_to_send_to_user = f"Here is your upload link: {upload_link}"

                        # --- CRITICAL FIX HERE: Create a DummyMessage object ---
                        dummy_message = SimpleNamespace(
                            content=message_to_send_to_user,
                            author=ctx.author, # The author of the command (staff)
                            attachments=[],
                            embeds=[]
                        )
                        # The reply method on the ticket object is designed to take a discord.Message-like object.
                        # DummyMessage simulates this.
                        await ticket.reply(dummy_message)
                        # ---------------------------------------------------
                        
                        view_embed = discord.Embed(
                            title="Staff View Link for Session",
                            description="Staff can use this link to view the uploaded images.",
                            color=discord.Color.green(), 
                            timestamp=discord.utils.utcnow() 
                        )
                        view_embed.add_field(name="Staff View Link", value=f"[Click Here]({view_link})", inline=False)
                        view_embed.set_footer(text=f"Session ID: {session_id}")
                        
                        await ctx.send(embed=view_embed) 

                        print(f"Log session created by {ctx.author} in ticket {ctx.channel.id} (Session ID: {session_id})")

                    else:
                        await ctx.send(f"Failed to create session: {data.get('error', 'Unknown error from server.')}")

        except aiohttp.ClientError as e:
            try:
                await processing_message.delete()
            except discord.NotFound:
                pass 
            await ctx.send(f"Network error communicating with CDN server: `{e}`. Please ensure the server is running.")
        except Exception as e:
            try:
                await processing_message.delete()
            except discord.NotFound:
                pass 
            await ctx.send(f"An unexpected error occurred: `{e}`. Please check bot logs.")
            print(f"Unexpected error in create_session_command: {e}")

async def setup(bot):
    await bot.add_cog(LogSession(bot))