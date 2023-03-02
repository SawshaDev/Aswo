import json
from typing import Optional
import discord
from discord.ext import commands
from bot import Aswo
from utils.subclasses import Context


class testinng(commands.Cog):
    def __init__(self, bot: Aswo):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def setprefix(self, ctx: Context, prefix: str):
        query = """
            INSERT INTO prefix (guild_id, prefix) VALUES($1, $2)
            ON CONFLICT(guild_id) DO 
            UPDATE SET prefix = excluded.prefix
        """
        await self.bot.pool.execute(query, ctx.guild.id, prefix)
        self.bot.prefixes[ctx.guild.id] = prefix
        await ctx.send(f'Succesfully made the guild prefix: ``{prefix.replace("/""/", "")}``')

    @commands.command()
    @commands.guild_only()
    async def raw(self, ctx: Context, message: Optional[discord.Message]):
        msg = message or ctx.reference
        data = json.dumps(await self.bot.http.get_message(ctx.channel.id, msg.id), indent=4)
        await ctx.send(f"```json\n{data}```")


async def setup(bot: Aswo):
    await bot.add_cog(testinng(bot))
