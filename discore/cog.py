"""
A simple and empty cog, pre-attributed
"""

from .bot import Bot, commands

__all__ = ('Cog',)


class Cog(commands.Cog):
    """
    creates an empty cog with a pre-attributed instance of the bot
    """

    def __init__(self, bot: Bot):
        self.bot = bot
