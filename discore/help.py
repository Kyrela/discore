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

    async def str_embed_footer(self, embed: discord.Embed):
        """
        Set the footer of the help message

        :param embed: the embed where to put the default message
        """
        embed.set_footer(
            text=f"{self.context.bot.user.name}" + (f" | ver. {self.config.version}" if self.config.version else ""),
            icon_url=self.context.bot.user.display_avatar.url
        )

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
                        self.context.clean_prefix + self.invoked_with, self.context.clean_prefix + self.invoked_with)
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

        await self.str_embed_footer(e)
        await self.get_destination().reply(embed=e, mention_author=False)

    async def send_cog_help(self, cog):
        """
        send the cog help message

        :param cog: the cog on which the help is called
        :return: None
        """

        filtered = await self.filter_commands(cog.get_commands())

        e = discord.Embed(
            title=self.config.help.cog.title.format(cog.qualified_name),
            description=cog.description,
            color=self.config.color
        )

        e.add_field(
            name=self.config.help.cog.commands,
            value=("`" + "`, `".join(elem.name for elem in filtered) + "`")
            if filtered else self.config.help.no_commands,
            inline=False
        )

        await self.str_embed_footer(e)
        await self.get_destination().reply(embed=e, mention_author=False)

    async def send_command_help(self, command: commands.Command):
        """
        Send the command help message

        :param command: the command on which the help is called
        :return: None
        """

        e = discord.Embed(
            title=self.config.help.command.title.format(command.name),
            description=(
                    (command.description + "\n\n" if command.description else "") +
                    f"```{self.get_command_signature(command)}```" +
                    ("\n" + command.help if command.help else "")
            ),
            color=self.config.color
        )

        await self.str_embed_footer(e)
        await self.get_destination().reply(embed=e, mention_author=False)

    async def send_group_help(self, group: commands.Group):
        """
        Send the command group help message

        :param group: the group on which the help is called
        :return: None
        """

        filtered = await self.filter_commands(group.commands)

        e = discord.Embed(
            title=group.qualified_name,
            description=group.description,
            color=self.config.color
        )

        e.add_field(
            name=self.config.help.group.title.format(group.qualified_name),
            value=("`" + "`, `".join(elem.name for elem in filtered) + "`")
            if filtered else self.config.help.no_commands,
            inline=False
        )

        await self.str_embed_footer(e)

        await self.get_destination().reply(embed=e, mention_author=False)

    async def command_not_found(self, string):
        """
        Return a message error when no corresponding command is found

        :param string: the called unknown command, cog or group
        :return: the message to send
        """

        return self.config.help.command.not_found.format(string)

    async def subcommand_not_found(self, command, string):
        """
        Return a message error when no corresponding subcommand is found

        :param command: the base command
        :param string: the unknown subcommand
        :return: the message to send
        """

        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return self.config.help.subcommand.not_found.format(command.qualified_name, string)
        return self.config.help.subcommand.no_subcommand.format(command.qualified_name)

    async def send_error_message(self, error: commands.CommandError):
        """
        Send the error message

        :param error: the error to send
        :return: None
        """

        e = discord.Embed(
            title=self.config.help.bot.title,
            description=error,
            color=self.config.color
        )

        await self.str_embed_footer(e)

        await self.get_destination().reply(embed=e, mention_author=False)
