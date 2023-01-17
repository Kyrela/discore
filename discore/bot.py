"""
The class representing the Discord bot
"""

import asyncio
import os
from os import path
import logging

from discord.ext import commands
import discord

from .help import EmbedHelpCommand
from .log import Log
from .utils import init_config, setup_logging, get_config

__all__ = ('Bot', 'config')

config = get_config()

_logger = logging.getLogger(__name__.split(".")[0])

class Bot(commands.Bot):
    """
    The class representing the Discord bot
    """

    class NoSpecifiedTokenError(Exception):
        """
        a basic custom error, in case no token is specified
        """
        pass

    def __init__(self, command_prefix: str = None, **kwargs):
        """
        Initialize the bot

        :param configuration_file: the toml file containing configuration information
        """

        global config
        config = init_config(**kwargs)
        setup_logging(**kwargs)
        global _logger
        _logger = logging.getLogger(__name__.split(".")[0])
        _logger.info("Bot initialising...")

        super().__init__(
            command_prefix=command_prefix or config.prefix,
            description=kwargs.pop('description', config.description) or None,
            intents=kwargs.pop('intents', discord.Intents.all()),
            help_command=kwargs.pop('help_command', EmbedHelpCommand(command_attrs=config.help.meta)),
            application_id=kwargs.pop('application_id', config.application_id) or None,
            **kwargs
        )

        asyncio.run(self._load_cogs(kwargs.pop('log', Log(self))))

    async def _load_cogs(self, log):
        """
        loads dynamically the cogs found in the /cog folder and the log cog
        """

        await self.add_cog(log)

        if path.isdir("cogs"):
            for file in os.listdir("cogs"):

                if not file.endswith(".py"):
                    continue

                cog_name = file[:-3]
                exec(f"from cogs.{cog_name} import {cog_name.title()}")
                new_cog = eval(f"{cog_name.title()}(self)")
                await self.add_cog(new_cog)

                help_cog_name = config.help.meta.cog or None
                if help_cog_name and help_cog_name.title() == cog_name.title():
                    self.help_command.cog = new_cog
                _logger.info(f"Cog {repr(cog_name)} loaded")

        if config.help.meta.cog and not self.help_command.cog:
            raise ModuleNotFoundError(
                f"The cog {repr(config.help.meta.cog)}, required by the help command, wasn't found")

    def run(self, token=None, **kwargs):
        """
        Runs the bot

        :return: None
        """

        token = token or config.token or None

        if not token:
            raise self.NoSpecifiedTokenError(
                "No token is specified in the configuration file nor in the run method")

        super().run(
            token,
            log_handler=None,
            **kwargs
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.run()
