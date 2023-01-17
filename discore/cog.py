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

    def __init__(self, bot: Bot, **kwargs):
        self.bot: Bot = bot
        super().__init__(**kwargs)
