"""
Represents the help class and all side-utilities related to the help
"""

import addict
import itertools

from discord.ext import commands
import discord

__all__ = ('EmbedHelpCommand',)


class EmbedHelpCommand(commands.HelpCommand):
    """
    represents a discord.py help system
    """

    def __init__(self, config: addict.Dict, **kwargs):
        """
        the base constructor for the class

        :param config: the configuration that contains the information
        """

        self.config = config
        super().__init__(**kwargs)

    def get_destination(self):
        """
        Return the destination of the help message

        :return: the destination of the help message
        """

        return self.context.message

    async def send_bot_help(self, mapping):
        """
        send the main help message

        :param mapping: contains unused informations
        :return: None
        """

        bot = self.context.bot

        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else self.config.help.bot.no_category

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        e = discord.Embed(
            title=self.config.help.bot.title,
            description=(
                    ((bot.description + "\n\n") if bot.description else "") +
                    self.config.help.bot.description.format(
                        self.clean_prefix + self.invoked_with, self.clean_prefix + self.invoked_with)
            ),
            color=self.config.color
        )

        for category, commands in to_iterate:
            e.add_field(
                name=category,
                value=("`" + "`, `".join(elem.name for elem in commands) + "`")
                if commands else self.config.help.no_commands,
                inline=False
            )

        e.set_footer(
            text=f"{self.context.bot.user.name}" + (f" | ver. {self.config.version}" if self.config.version else ""),
            icon_url=self.context.bot.user.avatar_url
        )
        await self.get_destination().reply(embed=e, mention_author=False)