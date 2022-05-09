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


class Bot(commands.Bot):
    """
    The class representing the Discord bot
    """

    class NoSpecifiedTokenError(Exception):
        """
        a basic custom error, in case no token is specified
        """
        pass

    def __init__(self, configuration_file: str = "config.toml"):
        """
        Initialize the bot

        :param configuration_file: the toml file containing configuration information
        """

        self.load_config(configuration_file)

        intents = discord.Intents.all()

        commands.Bot.__init__(
            self,
            command_prefix=self.config.prefix,
            description=self.config.description if 'description' in self.config else None,
            intents=intents
        )

        self.load_cogs()

    def load_config(self, configuration_file: str):
        """
        The configuration file loader

        :param configuration_file: the path to the configuration file
        """
        default_config = toml.load(path.join(path.dirname(__file__), "default_config.toml"))
        self.config = addict.Dict(merge(default_config, toml.load(configuration_file)))

    def load_cogs(self):
        """
        loads dynamically the cogs found in the /cog folder
        """
        if path.isdir("cogs"):
            for file in os.listdir("cogs"):
                if file[-3:] == ".py":
                    cog = file[:-3]
                    exec(f"from cogs.{cog} import {cog.title()}")
                    new_cog = eval(f"{cog.title()}(self)")
                    self.add_cog(new_cog)
                    if self.config.help.meta.cog.title() == cog.title():
                        exec("self.help_command.cog = new_cog")
        if self.config.help.meta.cog and not self.help_command.cog:
            raise ModuleNotFoundError(
                f"The cog {repr(self.config.help.meta.cog)}, required by the help command, wasn't found")

    def run(self):
        """
        Runs the bot

        :return: None
        """

        if 'token' in self.config:
            commands.Bot.run(self, self.config.token)
        else:
            raise self.NoSpecifiedTokenError("No token is specified in the configuration file")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.run()
