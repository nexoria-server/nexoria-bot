import time,discord
from collections import defaultdict,deque
from datetime import timedelta
from discord.ext import commands,tasks
from bot.utils import send_log
class Security(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.hist=defaultdict(lambda:deque(maxlen=12)); self.joins=defaultdict(deque); self.loop.start(); self.window=8; self.limit=6; self.mention_limit=5; self.duplicate=3; self.timeout=10
    def cog_unload(self): self.loop.cancel()
    @commands.Cog.listener()
    async def on_message(self,m):
        if not m.guild or m.author.bot or m.author.guild_permissions.manage_messages: return
        now=time.monotonic(); k=(m.guild.id,m.author.id); q=self.hist[k]; text=m.content.strip().lower(); q.append((now,text))
        while q and now-q[0][0]>self.window: q.popleft()
        mentions=len(m.mentions)+len(m.role_mentions)+(1 if m.mention_everyone else 0); dup=sum(1 for _,x in q if x and x==text)
        reason='Nachrichten-Spam' if len(q)>=self.limit else 'Mention-Spam' if mentions>=self.mention_limit else 'Wiederholung' if dup>=self.duplicate else None
        if not reason: return
        try: await m.delete(); await m.author.timeout(discord.utils.utcnow()+timedelta(minutes=self.timeout),reason='Anti-Spam: '+reason); await send_log(self.bot,m.guild,'🚫 Anti-Spam',f'{m.author.mention}: {reason}, Timeout {self.timeout} Min.',discord.Color.red())
        except discord.Forbidden: pass
        q.clear()
    @commands.Cog.listener()
    async def on_member_join(self,m):
        q=self.joins[m.guild.id]; now=time.monotonic(); q.append(now)
        while q and now-q[0]>20: q.popleft()
        if len(q)>=10: await send_log(self.bot,m.guild,'🚨 Möglicher Join-Raid',f'{len(q)} Joins in 20 Sekunden.',discord.Color.red())
    @tasks.loop(minutes=5)
    async def loop(self): pass
    @loop.before_loop
    async def before(self): await self.bot.wait_until_ready()
    @discord.app_commands.command(name='security',description='Zeigt Anti-Spam Status.')
    @discord.app_commands.default_permissions(manage_guild=True)
    async def security(self,i): await i.response.send_message(f'🚫 Anti-Spam aktiv — {self.limit} Nachrichten/{self.window}s, {self.mention_limit} Mentions, {self.timeout} Min. Timeout.',ephemeral=True)
async def setup(bot): await bot.add_cog(Security(bot))
