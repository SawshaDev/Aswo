from typing import Optional
import discord
from discord.ext import commands
from typing import Any, Union
from aiohttp import ClientSession
from asyncpg import Pool, Connection
from typing import TYPE_CHECKING
if TYPE_CHECKING:
	from bot import Aswo


class Context(commands.Context):
    channel: Union[discord.VoiceChannel, discord.TextChannel, discord.Thread, discord.DMChannel, discord.ForumChannel]
    prefix: str
    command: commands.Command[Any, ..., Any]
    bot: 'Aswo'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pool = self.bot.pool
        self._db: Optional[Union[Pool, Connection]]

    def __repr__(self) -> str:
        return '<Context>'

    @property
    def reference(self) -> Optional[discord.Message]:
        message = getattr(self.message.reference, "resolved", None)
        return isinstance(message, discord.Message) and message or None

    @property
    def session(self) -> ClientSession:
        return self.bot.session

    @property
    def db(self) -> Union[Pool, Connection]:
    	return self._db or self.pool
