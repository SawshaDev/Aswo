from bot import Aswo
import asyncio
import discord
import aiohttp
import config
import osu
import os
import asyncpg

discord.utils.setup_logging()

async def main():
    async with (aiohttp.ClientSession() as session, asyncpg.create_pool(config.POSTGRES_URI) as pool, osu.Client(client_id=config.OSU_CLIENT_ID, client_secret=config.OSU_CLIENT_SECRET) as osu_client, Aswo(session=session, osu=osu_client,pool=pool ) as bot):
        await bot.load_extension("jishaku")
        exts = [
            f"cogs.{ext[:-3] if ext.endswith('.py') else ext}"
            for ext in os.listdir("cogs")
            if not ext.startswith("_")
        ]
        for ext in exts:
            await bot.load_extension(ext)

        await bot.start(config.TOKEN, reconnect=True)

    

asyncio.run(main())