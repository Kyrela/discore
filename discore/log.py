"""
Represents the log class and all side-utilities related to the help
"""

from __future__ import annotations
import datetime
from os import path
import time
from textwrap import shorten
import traceback as tb
import sys
import logging

import discord
from discord.ext import commands

from .utils import get_config

__all__ = ('Log',)

config = get_config()

_logger = logging.getLogger(__name__.split(".")[0])


async def reply_with_fallback(ctx: commands.Context, message: str):
    """
    If the bot can't send a message to the channel, it will send it to the user instead

    :param ctx: commands.Context - The context of the command
    :type ctx: commands.Context
    :param message: The message to send
    :type message: str
    :return: The return value of the function.
    """
    try:
        return await ctx.reply(message, mention_author=False)
    except discord.errors.HTTPException:
        return await ctx.send(message)


def get_command_usage(prefix: str, command: commands.Command) -> str:
    """
    returns a command usage text for users

    :param prefix: the bot prefix
    :param command: the command on which the usage should be got
    :return: the command usage
    """
    parent = command.full_parent_name
    if len(command.aliases) > 0:
        aliases = '|'.join(command.aliases)
        fmt = '[%s|%s]' % (command.name, aliases)
        if parent:
            fmt = parent + ' ' + fmt
        alias = fmt
    else:
        alias = command.name if not parent else parent + ' ' + command.name

    return '%s%s %s' % (prefix, alias, command.signature)


class Log(commands.Cog,
          name="log",
          command_attrs=dict(hidden=True),
          description="Logs all the events happening with the bot"):
    """
    A class for handling a discord.py logging system
    """

    async def command_error(self, ctx: commands.Context, err: Exception) -> None:
        """
        Sends the internal command error to the raising channel and to the error channel

        :param ctx: the context of the command invocation
        :param err: the raised error
        :return: None
        """

        _logger.error(
            f"{repr(ctx.command.name)} command failed for "
            f"{repr(str(ctx.author))} ({repr(ctx.author.id)})", exc_info=err)

        error_data = tb.extract_tb(err.__traceback__)[1]
        error_filename = path.basename(error_data.filename)
        public_prompt = (
            f"File {error_filename!r}, "
            f"line {error_data.lineno}, "
            f"command {repr(error_data.name)}\n"
            f"{err.__class__.__name__} : {err}"
        )

        await reply_with_fallback(ctx, config.error.exception.format(public_prompt))

        if ctx.guild.me.guild_permissions.manage_guild \
                and await ctx.guild.invites() and config.log.create_invite:
            invite = (await ctx.guild.invites())[0].url
        elif ctx.channel.permissions_for(ctx.guild.me).create_instant_invite \
                 and config.log.create_invite:
            invite = await ctx.channel.create_invite(
                reason=config.error.invite_message,
                max_age=86400,
                max_uses=1,
                temporary=True,
                unique=False
            )
        else:
            invite = None

        if config.log.channel:
            embed = discord.Embed(title="Bug raised")
            embed.set_footer(
                text=f"{self.bot.user.name}" + (f" | ver. {config.version}" if config.version else ""),
                icon_url=self.bot.user.display_avatar.url
            )
            embed.add_field(name="Date", value=str(datetime.datetime.today())[:-7])
            embed.add_field(name="Server", value=f"{ctx.guild.name} ({ctx.guild.id})")
            embed.add_field(name="Command", value=error_data.name)
            embed.add_field(name="Author", value=f"{str(ctx.author)} ({ctx.author.id})")
            embed.add_field(name="File", value=error_data.filename)
            embed.add_field(name="Line", value=str(error_data.lineno))
            embed.add_field(name="Error", value=err.__class__.__name__)
            embed.add_field(name="Description", value=str(err))
            embed.add_field(name="Original message", value=ctx.message.content)
            embed.add_field(name="Link to message", value=ctx.message.jump_url)
            if invite:
                embed.add_field(name="Link to server", value=invite)
            await self.bot.get_channel(config.log.channel).send(
                "```\n" + "".join(tb.format_tb(err.__traceback__)).replace("```", "'''") + "\n```", embed=embed)

        _logger.error(
            f"Error context:\n"
            f"\tDate: {str(datetime.datetime.today())}\n"
            f"\tServer: {ctx.guild.name} ({ctx.guild.id})\n"
            f"\tCommand: {error_data.name}\n"
            f"\tAuthor: {str(ctx.author)} ({ctx.author.id})\n"
            f"\tFile: {error_data.filename}\n"
            f"\tLine: {error_data.lineno}\n"
            f"\tError: {err.__class__.__name__}\n"
            f"\tDescription: {str(err)}\n"
            f"\tOriginal message: {ctx.message.content}\n"
            f"\tLink to message: {ctx.message.jump_url}" +
            (f"\n\tLink to server: {invite}" if invite else ""))

    def __init__(self, bot: commands.Bot, **kwargs):
        """
        the base constructor for the class

        :param bot: The bot on which the logs should be added
        """

        self.bot = bot
        self.start_time = None
        global config
        config = get_config()
        super().__init__(**kwargs)

    @commands.Cog.listener()
    async def on_connect(self):
        _logger.info(f"Connected to Discord as \"{self.bot.user.name}\" (id : {self.bot.user.id})" +
                     (f" ver. {config.version}" if config.version else ""))

    @commands.Cog.listener()
    async def on_ready(self):
        self.start_time = time.time()
        if config.application_id:
            await self.bot.tree.sync()
        _logger.info(f"Bot loaded, ready to use (prefix '{self.bot.command_prefix}')")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if config.application_id:
            await self.bot.tree.sync()

    @commands.Cog.listener()
    async def on_disconnect(self):
        _logger.warning(f"Bot disconnected")

    @commands.Cog.listener()
    async def on_resumed(self):
        _logger.info(f"Bot reconnected")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        _logger.info(
            f"{repr(ctx.command.name)} command request sent by {repr(str(ctx.author))} ({repr(ctx.author.id)})" +
            f" with invocation {repr(ctx.message.content[len(self.bot.command_prefix):])}")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        rep = None
        async for message in ctx.history(limit=5):
            if message.author == ctx.me and message.reference and message.reference.message_id == ctx.message.id:
                rep = message
                break
        message_log_infos = []
        if rep:
            message_log_infos += [" with a response"]
            if rep.content:
                message_log_infos += [f"starting with the text "
                                      f"'{shorten(repr(rep.content)[1:-1], width=120, placeholder='...')}'"]
            for embed in rep.embeds:
                message_log_infos += [
                    f"containing an embed with name {repr(embed.title)}, "
                    f"and with description starting with "
                    f"'{shorten(repr(embed.description)[1:-1], width=120, placeholder='...')}'"]
            for attachment in rep.attachments:
                message_log_infos += [
                    f"containing an file with name {repr(attachment.filename)} (url {repr(attachment.url)})"]

        _logger.info(
            f"{repr(ctx.command.name)} command succeeded for {repr(str(ctx.author))} ({repr(ctx.author.id)})" +
            ", ".join(message_log_infos))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error: Exception):
        if isinstance(error, commands.ConversionError) or isinstance(error, commands.BadArgument):
            await reply_with_fallback(ctx, config.error.bad_argument.format(
                get_command_usage(self.bot.command_prefix, ctx.command),
                self.bot.command_prefix + "help " + ctx.command.name))
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"Bad arguments given")
        elif isinstance(error, commands.MissingRequiredArgument):
            await reply_with_fallback(ctx, config.error.missing_argument.format(
                get_command_usage(self.bot.command_prefix, ctx.command),
                self.bot.command_prefix + "help " + ctx.command.name))
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"Missing required argument")
        elif (isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden)) or \
                isinstance(error, commands.BotMissingPermissions):
            await reply_with_fallback(ctx, config.error.bot.missing_permission)
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"Bot is missing permissions")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
            await reply_with_fallback(ctx, config.error.not_found)
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"No matches for the request")
        elif isinstance(error, commands.NotOwner) or isinstance(error, commands.NotOwner) or \
                isinstance(error, commands.MissingPermissions):
            await reply_with_fallback(ctx, config.error.user.missing_permission)
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"User is missing permissions")
        elif isinstance(error, commands.CommandOnCooldown):
            await reply_with_fallback(ctx, config.error.on_cooldown.format(error.retry_after))
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"On cooldown")
        elif isinstance(error, commands.InvalidEndOfQuotedStringError):
            await reply_with_fallback(ctx, config.error.invalid_quoted_string)
            _logger.warning(
                f"{repr(ctx.command.name)} command failed for {repr(str(ctx.author))} ({repr(ctx.author.id)}): "
                f"Invalid quoted string")
        elif not isinstance(error, commands.CommandNotFound):
            if isinstance(error, commands.CommandInvokeError):
                error = error.original
            await self.command_error(ctx, error)

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        err = sys.exc_info()[2]
        _logger.error(f"Error raised:", exc_info=sys.exc_info()[1])
        _logger.error(f"Error context:\n\targs: {repr(args)}\n\tkargs: {repr(kwargs)}")
        if config.log.channel:
            embed = discord.Embed(title="Bug raised")
            embed.set_footer(
                text=f"{self.bot.user.name}" + (f" | ver. {config.version}" if config.version else ""),
                icon_url=self.bot.user.display_avatar.url
            )
            embed.add_field(name="Date", value=str(datetime.datetime.today())[:-7])
            embed.add_field(name="Event", value=event)
            embed.add_field(name="File", value=tb.extract_tb(err)[1].filename)
            embed.add_field(name="Line", value=str(tb.extract_tb(err)[1].lineno))
            embed.add_field(name="Error", value=sys.exc_info()[0].__name__)
            embed.add_field(name="Description", value=str(sys.exc_info()[1]))
            embed.add_field(name="Arguments", value=f"{repr(args)}\n\n{repr(kwargs)}")
            await self.bot.get_channel(config.log.channel).send(
                "```" + "".join(tb.format_tb(err)) + "```", embed=embed)
