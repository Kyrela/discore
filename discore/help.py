"""
Represents the help class and all side-utilities related to the help
"""

import addict

from discord.ext import commands
import discord

__all__ = ('EmbedHelpCommand',)


class EmbedHelpCommand(commands.HelpCommand):
    """
    represents a discord.py help system
    """

    def __init__(self, config: addict.Dict, **kargs):
        """
        the base constructor for the class

        :param config: the configuration that contains the information
        """

        self.config = config
        super().__init__(**kargs)
