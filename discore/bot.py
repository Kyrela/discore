"""
The class representing the Discord bot
"""

__all__ = ('Bot',)

from discord.ext import commands
import discord


class Bot(commands.Bot):
    """
    The class representing the Discord bot
    """

    def __init__(self, token):
        """
        Initialize the bot
        """

        self.token = token

        intents = discord.Intents.all()

        commands.Bot.__init__(
            self,
            command_prefix="!",
            intents=intents
        )

    def run(self):
        """
        Runs the bot

        :return: None
        """

        commands.Bot.run(self, self.token)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.run()
