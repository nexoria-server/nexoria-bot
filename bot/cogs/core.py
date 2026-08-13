import discord
from discord import app_commands
from discord.ext import commands
from bot.config import settings
from bot.embeds import success,info
class Core(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='ping',description='Zeigt die Bot-Latenz.')
    async def ping(self,i): await i.response.send_message(f'🏓 Pong! `{round(self.bot.latency*1000)} ms`',ephemeral=True)
    @app_commands.command(name='config',description='Konfiguriert Bot-Kanäle und Rollen.')
    @app_commands.default_permissions(manage_guild=True)
    async def config(self,i,logs:discord.TextChannel=None,tickets:discord.CategoryChannel=None,applications:discord.TextChannel=None,ticket_staff:discord.Role=None,application_staff:discord.Role=None):
        if not any([logs,tickets,applications,ticket_staff,application_staff]):
            c=await self.bot.db.guild_config(i.guild.id); return await i.response.send_message(embed=info('Konfiguration',f"Logs: <#{c['log_channel_id']}>\nTickets Kategorie-ID: `{c['ticket_category_id']}`\nBewerbungen: <#{c['application_channel_id']}>\nTicket-Team: <@&{c['ticket_staff_role_id']}>\nBewerbungs-Team: <@&{c['application_staff_role_id']}>"),ephemeral=True)
        for obj,field in [(logs,'log_channel_id'),(tickets,'ticket_category_id'),(applications,'application_channel_id'),(ticket_staff,'ticket_staff_role_id'),(application_staff,'application_staff_role_id')]:
            if obj: await self.bot.db.set_config(i.guild.id,field,obj.id)
        await i.response.send_message(embed=success('Gespeichert','Die Konfiguration wurde aktualisiert.'),ephemeral=True)
    @commands.Cog.listener()
    async def on_ready(self): await self.bot.change_presence(activity=discord.Game(name=settings.BOT_STATUS))
async def setup(bot): await bot.add_cog(Core(bot))
