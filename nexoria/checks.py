from __future__ import annotations

import discord

from .database import Database


async def allowed(interaction: discord.Interaction, db: Database, purpose: str) -> bool:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    configured = await db.roles(interaction.guild.id, f"permission.{purpose}")
    return bool(configured & {role.id for role in interaction.user.roles})


async def require(interaction: discord.Interaction, db: Database, purpose: str) -> bool:
    if await allowed(interaction, db, purpose):
        return True
    text = "Du hast keine Berechtigung für diese Aktion."
    if interaction.response.is_done():
        await interaction.followup.send(text, ephemeral=True)
    else:
        await interaction.response.send_message(text, ephemeral=True)
    return False


async def safe_dm(user: discord.abc.Messageable, *, embed: discord.Embed) -> bool:
    try:
        await user.send(embed=embed)
        return True
    except (discord.Forbidden, discord.HTTPException):
        return False
