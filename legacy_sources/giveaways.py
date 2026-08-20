import random,time,discord
from discord import app_commands
from discord.ext import commands,tasks
class GiveawayView(discord.ui.View):
    def __init__(self,bot): super().__init__(timeout=None); self.bot=bot
    @discord.ui.button(label='Teilnehmen',emoji='🎁',style=discord.ButtonStyle.success,custom_id='giveaway:enter')
    async def enter(self,i,b):
        try: await self.bot.db.execute('INSERT INTO giveaway_entries VALUES(?,?)',(i.message.id,i.user.id)); await i.response.send_message('🎉 Du bist dabei!',ephemeral=True)
        except Exception: await i.response.send_message('Du bist bereits dabei.',ephemeral=True)
class Giveaways(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.loop.start(); bot.add_view(GiveawayView(bot))
    def cog_unload(self): self.loop.cancel()
    @app_commands.command(name='giveaway',description='Startet oder beendet ein Giveaway.')
    @app_commands.choices(aktion=[app_commands.Choice(name='Start',value='start'),app_commands.Choice(name='Ende',value='end')])
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway(self,i,aktion:app_commands.Choice[str],minuten:int=None,gewinner:int=None,preis:str=None):
        if aktion.value=='start':
            if not minuten or not gewinner or not preis: return await i.response.send_message('Start benötigt Minuten, Gewinner und Preis.',ephemeral=True)
            end=time.time()+minuten*60; e=discord.Embed(title='🎁 Giveaway',description=f'**Preis:** {preis}\n**Gewinner:** {gewinner}\n**Ende:** <t:{int(end)}:R>',color=discord.Color.gold()); await i.response.send_message(embed=e,view=GiveawayView(self.bot)); m=await i.original_response(); await self.bot.db.execute('INSERT INTO giveaways VALUES(?,?,?,?,?,0)',(m.id,i.guild.id,i.channel.id,preis,end,gewinner)); return
        rows=await self.bot.db.fetchall('SELECT message_id FROM giveaways WHERE channel_id=? AND ended=0 ORDER BY end_at DESC',(i.channel.id,));
        if rows: await self.finish(rows[0]['message_id']); await i.response.send_message('🎁 Giveaway beendet.',ephemeral=True)
        else: await i.response.send_message('Kein aktives Giveaway.',ephemeral=True)
    @tasks.loop(seconds=30)
    async def loop(self):
        for r in await self.bot.db.fetchall('SELECT message_id FROM giveaways WHERE ended=0 AND end_at<=?',(time.time(),)): await self.finish(r['message_id'])
    @loop.before_loop
    async def before(self): await self.bot.wait_until_ready()
    async def finish(self,mid):
        r=await self.bot.db.fetchone('SELECT * FROM giveaways WHERE message_id=?',(mid,));
        if not r or r['ended']: return
        entries=await self.bot.db.fetchall('SELECT user_id FROM giveaway_entries WHERE message_id=?',(mid,)); picks=random.sample(entries,min(r['winners'],len(entries))) if entries else []; ch=self.bot.get_channel(r['channel_id'])
        if ch: await ch.send(f"🎉 Giveaway beendet! **{r['prize']}** — Gewinner: {', '.join(f'<@{x["user_id"]}>' for x in picks) if picks else 'keine'}")
        await self.bot.db.execute('UPDATE giveaways SET ended=1 WHERE message_id=?',(mid,))
async def setup(bot): await bot.add_cog(Giveaways(bot))
