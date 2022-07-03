"""
A simple and empty cog, pre-attributed
"""

from discord.ext import commands

__all__ = ('Cog',)


class Cog(commands.Cog):
    """
    creates an empty cog with a pre-attributed instance of the bot
    """

    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        super().__init__()
