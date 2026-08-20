import discord
from discord.ext import commands
from bot.utils import send_log
class Logs(commands.Cog):
    def __init__(self,bot): self.bot=bot
    @commands.Cog.listener()
    async def on_member_join(self,m): await send_log(self.bot,m.guild,'📥 Join',f'{m.mention} ({m.id})',discord.Color.green())
    @commands.Cog.listener()
    async def on_member_remove(self,m): await send_log(self.bot,m.guild,'📤 Leave',f'{m} ({m.id})',discord.Color.red())
    @commands.Cog.listener()
    async def on_message_delete(self,m):
        if m.guild and not m.author.bot: await send_log(self.bot,m.guild,'🗑️ Nachricht gelöscht',f'{m.author.mention} in {m.channel.mention}\n{(m.content or "*kein Text*")[:1500]}',discord.Color.orange())
    @commands.Cog.listener()
    async def on_message_edit(self,b,a):
        if b.guild and not b.author.bot and b.content!=a.content: await send_log(self.bot,b.guild,'✏️ Nachricht bearbeitet',f'{b.author.mention} in {b.channel.mention}\nVorher: {b.content[:700]}\nNachher: {a.content[:700]}',discord.Color.orange())
async def setup(bot): await bot.add_cog(Logs(bot))
