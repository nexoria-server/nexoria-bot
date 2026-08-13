import discord
def success(title,description): return discord.Embed(title='✅ '+title,description=description,color=discord.Color.green())
def info(title,description): return discord.Embed(title='ℹ️ '+title,description=description,color=discord.Color.blurple())
