from __future__ import annotations
import datetime
import sys
from typing import TYPE_CHECKING
from typing_extensions import Self
import discord
from discord.ext import commands, tasks
import aiohttp
import pkg_resources
import typing
import logging
import os
import asyncpg
import socketio
from config import replay_key
from osu import Client
import utils




intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.typing = False
intents.presences = True


class Aswo(commands.Bot):
    """Base aswo bot subclass!"""
    def __init__(
        self, 
        *, 
        session: aiohttp.ClientSession,
        osu: Client,
        pool: asyncpg.Pool
    ):
        self.session = session
        self._connected = False
        self.osu: Client = osu
        self.pool = pool
        self.startup_time: typing.Optional[datetime.timedelta] = None
        self.start_time = discord.utils.utcnow()
        self.logger = logging.getLogger(__name__)
        self.replay_key = replay_key

        self._default_prefixes = (">>",)


        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_NO_DM_TRACEBACK"] = "True"
        
        super().__init__(command_prefix=self.get_pre,intents=intents, activity=discord.Activity(type=discord.ActivityType.playing, name="Click on the circles!"), owner_ids = [894794517079793704, 739219467455823921])



    async def get_pre(self, bot, message: discord.Message):
        if not message:
            return commands.when_mentioned_or(*self._default_prefixes)(bot, message)
        if not message.guild:
            return commands.when_mentioned_or(*self._default_prefixes)(bot, message)

        try:
            prefix = (*self._default_prefixes, self.prefixes[message.guild.id], )
        except KeyError:
            prefix = self._default_prefixes

        return commands.when_mentioned_or(*prefix)(bot, message)

    async def setup_hook(self): 
        query = await self.pool.fetch("SELECT * FROM prefix")
        self.prefixes = {
            x['guild_id']: x['prefix']
            for x in query
        }

    async def get_context(self, message, *, cls=utils.Context ):
        return await super().get_context(message, cls=cls)

    async def on_ready(self):
        if not hasattr(self, 'uptime'):
            self.uptime = discord.utils.utcnow()
    
        if self._connected:
            msg = f"Bot reconnected at {datetime.datetime.now().strftime('%b %d %Y %H:%M:%S')}"
            self.logger.info(msg)       
        else:
            self._connected = True
            self.startup_time = discord.utils.utcnow() - self.start_time
            msg = (
                f"Successfully logged into {self.user}. ({round(self.latency * 1000)}ms)\n"
                f"Discord.py Version: {discord.__version__} | {pkg_resources.get_distribution('discord.py').version}\n"
                f"Python version: {sys.version}\n"
                f"Startup Time: {self.startup_time.total_seconds():.2f} seconds."
            )
            self.logger.info(f"{msg}")
            
            for extension in self.cogs:
                self.logger.info(f" - Loaded cogs.{extension.lower()}")