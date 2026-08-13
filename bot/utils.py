import discord
async def send_log(bot,guild,title,description,color=None):
    cfg=await bot.db.guild_config(guild.id); cid=int(cfg['log_channel_id'] or 0); ch=guild.get_channel(cid) if cid else None
    if ch:
        try: await ch.send(embed=discord.Embed(title=title,description=description,color=color or discord.Color.blurple(),timestamp=discord.utils.utcnow()))
        except discord.HTTPException: pass
