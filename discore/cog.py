"""
A simple and empty cog, pre-attributed
"""

from discord.ext.commands import Cog as _Cog
from .bot import Bot

__all__ = ('Cog',)


class Cog(_Cog):
    """
    creates an empty cog with a pre-attributed instance of the bot
    """

    @property
    def bot(self) -> Bot:
        """
        Returns the bot instance

        :return: Bot
        """
        return Bot.get()
