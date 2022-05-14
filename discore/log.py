"""
Represents the log class and all side-utilities related to the help
"""
from __future__ import annotations

import datetime
import time
import addict

import discord
from discord.ext import commands


class Log:
    """
    A class for handling a discord.py logging system
    """

    def write(self, *values: object, start: str | None = '', **kwargs) -> None:
        """
        print(value, ..., start='', sep=' ', end='\n', file=sys.stdout, flush=False)

        :param values: The elements to write in the log
        :param start: string appended before the first value, default nothing
        :param file:  a file-like object (stream); defaults to the current sys.stdout.
        :param sep:   string inserted between values, default a space.
        :param end:   string appended after the last value, default a newline.
        :param flush: whether to forcibly flush the stream.
        """

        values = ((start or '') + f"[{str(datetime.datetime.today())}]", *values)

        print(*values, **kwargs)

        if self.config.log.file:
            kwargs.pop('file', None)
            with open(self.config.log.file, "a+", encoding="utf-8") as f:
                print(*values, file=f, **kwargs)

    def __init__(self, bot: commands.Bot, config: addict.Dict):
        """
        the base constructor for the class

        :param bot: The bot on which the logs should be added
        :param config: the configuration
        """

        self.bot = bot
        self.config = config

        @self.bot.event
        async def on_connect():
            self.write(f"Connected to Discord as \"{bot.user.name}\" (id : {bot.user.id})" +
                       (f" ver. {self.config.version}" if self.config.version else ""))

        @self.bot.event
        async def on_ready():
            self.start_time = time.time()
            self.write(f"Bot loaded, ready to use (prefix '{self.config.prefix}')")

        @self.bot.event
        async def on_disconnect():
            self.write(f"Bot disconnected")

        @self.bot.event
        async def on_resumed():
            self.write(f"Bot reconnected")
