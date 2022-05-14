"""
The class representing the Discord bot
"""

__all__ = ('Bot',)

import os
from os import path
import toml
import addict
from mergedeep import merge

from discord.ext import commands
import discord

from .help import EmbedHelpCommand
from .log import Log


def load_config(configuration_file: str) -> addict.Dict:
    """
    The configuration file loader

    :param configuration_file: the path to the configuration file
    :return: the configuration as an addict.Dict
    """
    default_config = toml.load(path.join(path.dirname(__file__), "default_config.toml"))
    return addict.Dict(merge(default_config, toml.load(configuration_file)))


class Bot(commands.Bot):
    """
    The class representing the Discord bot
    """

    class NoSpecifiedTokenError(Exception):
        """
        a basic custom error, in case no token is specified
        """
        pass

    def __init__(self, configuration_file: str = "config.toml", **kwargs):
        """
        Initialize the bot

        :param configuration_file: the toml file containing configuration information
        """

        self.config = load_config(configuration_file)
        self.log = kwargs.pop('log', None) or Log(self, self.config)
        self.log.write("Bot initialising...", start="\n")

        super().__init__(
            command_prefix=kwargs.pop('command_prefix', None) or self.config.prefix,
            description=kwargs.pop('description', None) or self.config.description or None,
            intents=kwargs.pop('intents', None) or discord.Intents.all(),
            help_command=kwargs.pop('help_command', None) or EmbedHelpCommand(
                self.config, command_attrs=self.config.help.meta),
            **kwargs
        )

        self.load_cogs()

    def load_cogs(self):
        """
        loads dynamically the cogs found in the /cog folder
        """

        if path.isdir("cogs"):
            for file in os.listdir("cogs"):

                if not file.endswith(".py"):
                    continue

                cog_name = file[:-3]
                exec(f"from cogs.{cog_name} import {cog_name.title()}")
                new_cog = eval(f"{cog_name.title()}(self)")
                self.add_cog(new_cog)

                help_cog_name = self.config.help.meta.cog or None
                if help_cog_name and help_cog_name.title() == cog_name.title():
                    self.help_command.cog = new_cog

        if self.config.help.meta.cog and not self.help_command.cog:
            raise ModuleNotFoundError(
                f"The cog {repr(self.config.help.meta.cog)}, required by the help command, wasn't found")

    def run(self, token=None, **kwargs):
        """
        Runs the bot

        :return: None
        """

        token = token or self.config.token or None

        if not token:
            raise self.NoSpecifiedTokenError("No token is specified in the configuration file")

        super().run(self.config.token, **kwargs)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.run()
