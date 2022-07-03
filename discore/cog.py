"""
A simple and empty cog, pre-attributed
"""

from discord.ext import commands
from .bot import Bot

__all__ = ('Cog',)


class Cog(commands.Cog):
    """
    creates an empty cog with a pre-attributed instance of the bot
    """

    def __init__(self, bot: Bot):
        self.bot: Bot = bot
        super().__init__()
