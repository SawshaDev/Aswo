import discord
from discord.ext import commands
from .osu import osu


class Osu(osu):
    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Osu(bot))