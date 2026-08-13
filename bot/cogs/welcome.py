import discord
from discord.ext import commands

from bot.config import settings

WELCOME_CHANNEL_ID = settings.WELCOME_CHANNEL_ID
LEAVE_CHANNEL_ID = settings.LEAVE_CHANNEL_ID


class Welcome(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not WELCOME_CHANNEL_ID:
            return

        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)

        if channel is None:
            print(
                f"[Welcome] Welcome-Kanal "
                f"{WELCOME_CHANNEL_ID} nicht gefunden."
            )
            return

        embed = discord.Embed(
            title="👋 Willkommen bei Nexoria!",
            description=(
                f"Herzlich willkommen, {member.mention}! 🎉\n\n"
                f"Schön, dass du **{member.guild.name}** "
                "beigetreten bist.\n\n"
                "Wir wünschen dir viel Spaß in unserer "
                "Community und hoffen, dass du dich schnell "
                "bei uns zurechtfindest. 💙"
            ),
            color=discord.Color.blurple(),
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="👤 Mitglied",
            value=member.mention,
            inline=True,
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(member.guild.member_count),
            inline=True,
        )

        embed.set_footer(
            text="Nexoria Community • Willkommen!",
        )

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not LEAVE_CHANNEL_ID:
            return

        channel = member.guild.get_channel(LEAVE_CHANNEL_ID)

        if channel is None:
            print(
                f"[Welcome] Leave-Kanal "
                f"{LEAVE_CHANNEL_ID} nicht gefunden."
            )
            return

        embed = discord.Embed(
            title="👋 Auf Wiedersehen!",
            description=(
                f"**{member.display_name}** hat die "
                f"**{member.guild.name}** Community verlassen.\n\n"
                "Wir wünschen dir weiterhin alles Gute "
                "und vielleicht sieht man sich wieder! 💙"
            ),
            color=discord.Color.dark_grey(),
        )

        embed.set_thumbnail(
            url=member.display_avatar.url
        )

        embed.add_field(
            name="👤 Mitglied",
            value=member.mention,
            inline=True,
        )

        embed.add_field(
            name="👥 Mitglieder",
            value=str(member.guild.member_count),
            inline=True,
        )

        embed.set_footer(
            text="Nexoria Community • Bis bald!",
        )

        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Welcome(bot))
