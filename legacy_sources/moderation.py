import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
from bot.embeds import success
from bot.utils import send_log
class Moderation(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @app_commands.command(name='warn',description='Verwarnt ein Mitglied.')
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self,i,member:discord.Member,grund:str):
        await self.bot.db.execute('INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)',(i.guild.id,member.id,i.user.id,grund)); await i.response.send_message(embed=success('Warnung',f'{member.mention} wurde verwarnt.')); await send_log(self.bot,i.guild,'⚠️ Warnung',f'{member.mention} durch {i.user.mention}\n**Grund:** {grund}',discord.Color.orange())
    @app_commands.command(name='warnings',description='Zeigt Warnungen eines Mitglieds.')
    @app_commands.default_permissions(moderate_members=True)
    async def warnings(self,i,member:discord.Member):
        rows=await self.bot.db.fetchall('SELECT reason,moderator_id,created_at FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 15',(i.guild.id,member.id))
        if not rows: return await i.response.send_message('Keine Warnungen.',ephemeral=True)
        await i.response.send_message('\n'.join(f"• {r['reason']} — <@{r['moderator_id']}> ({r['created_at']})" for r in rows),ephemeral=True)
    @app_commands.command(name='timeout',description='Setzt einen Timeout.')
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self,i,member:discord.Member,minuten:app_commands.Range[int,1,40320],grund:str='Kein Grund angegeben'):
        await member.timeout(discord.utils.utcnow()+timedelta(minutes=minuten),reason=grund); await i.response.send_message(embed=success('Timeout',f'{member.mention}: {minuten} Minuten.')); await send_log(self.bot,i.guild,'⏱️ Timeout',f'{member.mention} durch {i.user.mention}\n{grund}',discord.Color.orange())
    @app_commands.command(name='kick',description='Kickt ein Mitglied.')
    @app_commands.default_permissions(kick_members=True)
    async def kick(self,i,member:discord.Member,grund:str='Kein Grund angegeben'):
        await member.kick(reason=grund); await i.response.send_message(embed=success('Kick',f'{member} wurde gekickt.')); await send_log(self.bot,i.guild,'👢 Kick',f'{member} durch {i.user.mention}\n{grund}',discord.Color.red())
    @app_commands.command(name='ban',description='Bannt ein Mitglied.')
    @app_commands.default_permissions(ban_members=True)
    async def ban(self,i,member:discord.Member,grund:str='Kein Grund angegeben'):
        await member.ban(reason=grund); await i.response.send_message(embed=success('Ban',f'{member} wurde gebannt.')); await send_log(self.bot,i.guild,'🔨 Ban',f'{member} durch {i.user.mention}\n{grund}',discord.Color.red())
    @app_commands.command(name='clear',description='Löscht bis zu 100 Nachrichten.')
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self,i,anzahl:app_commands.Range[int,1,100]):
        await i.response.defer(ephemeral=True); deleted=await i.channel.purge(limit=anzahl); await i.followup.send(f'🧹 {len(deleted)} Nachrichten gelöscht.',ephemeral=True)
async def setup(bot): await bot.add_cog(Moderation(bot))
