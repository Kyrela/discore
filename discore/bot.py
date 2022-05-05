"""
The class representing the Discord bot
"""

__all__ = ('Bot',)

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

    def __init__(self, configuration_file="config.toml"):
        """
        Initialize the bot
        """

        default_config = toml.load(path.join(path.dirname(__file__), "default_config.toml"))
        self.config = addict.Dict(merge(default_config, toml.load(configuration_file)))

        intents = discord.Intents.all()

        commands.Bot.__init__(
            self,
            command_prefix=self.config.prefix,
            description=self.config.description if 'description' in self.config else None,
            intents=intents
        )

    def run(self):
        """
        Runs the bot

        :return: None
        """

        commands.Bot.run(self, self.config.token)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.run()
