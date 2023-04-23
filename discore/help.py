"""
Represents the help class and all side-utilities related to the help
"""

import itertools

from discord.ext import commands
import discord

from .utils import config, reply_with_fallback, t

__all__ = ('EmbedHelpCommand',)


class EmbedHelpCommand(commands.HelpCommand):
    """
    represents a discord.py help system
    """

    def __init__(self, **kwargs):
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
            text=f"{self.context.bot.user.name}" + (f" | ver. {config.version}" if config.version else ""),
            icon_url=self.context.bot.user.display_avatar.url
        )

    async def send_bot_help(self, mapping):
        """
        send the main help message

        :param mapping: contains unused informations
        :return: None
        """

        ctx = self.context
        bot = ctx.bot

        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else t(ctx, "help.bot.no_category")

        filtered = await self.filter_commands(bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        e = discord.Embed(
            title=t(ctx, "help.bot.title"),
            description=(
                ((bot.description + "\n\n") if bot.description else "") +
                t(ctx, "help.bot.description", help_command=self.context.clean_prefix + self.invoked_with)),
            color=config.color
        )

        for category, commands in to_iterate:
            e.add_field(
                name=category,
                value=("`" + "`, `".join(elem.name for elem in commands) + "`")
                if commands else t("help.no_commands"),
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

        ctx = self.context

        filtered = await self.filter_commands(cog.get_commands())

        e = discord.Embed(
            title=t(ctx, "help.cog.title", cog=cog.qualified_name),
            description=cog.description,
            color=config.color
        )

        e.add_field(
            name=t(ctx, "help.cog.commands"),
            value=("`" + "`, `".join(elem.name for elem in filtered) + "`")
            if filtered else t(ctx, "help.no_commands"),
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
            title=t(self.context, "help.command.title", command=command.name),
            description=(
                    (command.description + "\n\n" if command.description else "") +
                    f"```{self.get_command_signature(command)}```" +
                    ("\n" + command.help if command.help else "")
            ),
            color=config.color
        )

        await self.str_embed_footer(e)
        await self.get_destination().reply(embed=e, mention_author=False)

    async def send_group_help(self, group: commands.Group):
        """
        Send the command group help message

        :param group: the group on which the help is called
        :return: None
        """

        ctx = self.context

        filtered = await self.filter_commands(group.commands)

        e = discord.Embed(
            title=group.qualified_name,
            description=group.description,
            color=config.color
        )

        e.add_field(
            name=t(ctx, "help.group.title", group=group.qualified_name),
            value=("`" + "`, `".join(elem.name for elem in filtered) + "`")
            if filtered else t(ctx, "help.no_commands"),
            inline=False
        )

        await self.str_embed_footer(e)

        await self.get_destination().reply(embed=e, mention_author=False)

    async def command_not_found(self, command_name):
        """
        Return a message error when no corresponding command is found

        :param command_name: the called unknown command, cog or group
        :return: the message to send
        """

        return t(self.context, "help.command.not_found", command=command_name)

    async def subcommand_not_found(self, command, subcommand_name):
        """
        Return a message error when no corresponding subcommand is found

        :param command: the base command
        :param subcommand_name: the unknown subcommand
        :return: the message to send
        """

        ctx = self.context

        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return t(ctx, "help.subcommand.not_found", command=command.qualified_name, subcommand=subcommand_name)
        return t(ctx, "help.subcommand.no_subcommand", command=command.qualified_name)

    async def send_error_message(self, error: commands.CommandError):
        """
        Send the error message

        :param error: the error to send
        :return: None
        """

        e = discord.Embed(
            title=t(self.context, "help.bot.title"),
            description=error,
            color=config.color
        )

        await self.str_embed_footer(e)

        await reply_with_fallback(self.context, embed=e)
