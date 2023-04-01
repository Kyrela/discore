"""
The class representing the Discord bot
"""

import asyncio
import os
import sys
from os import path
import logging
import time
from typing import Union
from i18n import t
from datetime import datetime
import traceback as tb

from discord.ext import commands
import discord

from .help import EmbedHelpCommand
from .command_tree import CommandTree
from .utils import (
    init_config, setup_logging, get_config,
    reply_with_fallback, get_command_usage,
    sanitize)

__all__ = ('Bot', 'config')

config = get_config()

_log = logging.getLogger(__name__)


class Bot(commands.Bot):
    """
    The class representing the Discord bot
    """

    class NoSpecifiedTokenError(Exception):
        """
        a basic custom error, in case no token is specified
        """
        pass

    def __init__(self, command_prefix: str = None, **kwargs):
        """
        Initialize the bot

        :param configuration_file: the toml file containing configuration information
        """

        self.start_time = None

        global config
        config = init_config(**kwargs)
        setup_logging(**kwargs)
        global _log
        _log = logging.getLogger(__name__)
        _log.info("Bot initialising...")

        super().__init__(
            command_prefix=command_prefix or config.prefix,
            description=kwargs.pop('description', config.description) or None,
            intents=kwargs.pop('intents', discord.Intents.all()),
            help_command=kwargs.pop('help_command', EmbedHelpCommand(command_attrs=config.help.meta)),
            tree_cls=kwargs.pop('tree_cls', CommandTree),
            **kwargs
        )

        asyncio.run(self._load_cogs())

    async def _load_cogs(self):
        """
        loads dynamically the cogs found in the /cog folder and the log cog
        """

        if path.isdir("cogs"):
            for file in os.listdir("cogs"):

                if not file.endswith(".py"):
                    continue

                cog_name = file[:-3]
                exec(f"from cogs.{cog_name} import {cog_name.title()}")
                new_cog = eval(f"{cog_name.title()}(self)")
                await self.add_cog(new_cog)

                help_cog_name = config.help.meta.cog or None
                if help_cog_name and help_cog_name.title() == cog_name.title():
                    self.help_command.cog = new_cog
                _log.info(f"Cog {cog_name!r} loaded")

        if config.help.meta.cog and not self.help_command.cog:
            raise ModuleNotFoundError(
                f"The cog {config.help.meta.cog!r}, required by the help command, wasn't found")

    def run(self, token=None, **kwargs):
        """
        Runs the bot

        :return: None
        """

        token = token or config.token or None

        if not token:
            raise self.NoSpecifiedTokenError(
                "No token is specified in the configuration file nor in the run method")

        super().run(
            token,
            log_handler=None,
            **kwargs
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.run()

    async def on_connect(self):
        _log.info(
            f"Connected to Discord as {self.user.name!r} "
            f"(id : {self.user.id!r})"
            + (f" ver. {config.version}" if config.version else ""))

    async def on_ready(self):
        self.start_time = time.time()
        if self.application_id:
            if not await self.tree.sync():
                _log.error("Failed to sync the tree")
        _log.info(f"Bot loaded, ready to use (prefix {self.command_prefix!r})")

    async def on_guild_join(self, guild: discord.Guild):
        if self.application_id:
            await self.tree.sync(guild=guild)

    async def on_disconnect(self):
        _log.warning(f"Bot disconnected")

    async def on_resumed(self):
        _log.info("Bot resumed")

    async def on_command(self, ctx: commands.Context):
        if ctx.interaction:
            _log.info(
                f"{ctx.command.name!r} slash command request sent by "
                f"{str(ctx.author)!r} ({ctx.author.id!r}) with invocation "
                f"{str(ctx.kwargs)!r}")
            return
        _log.info(
            f"{ctx.command.name!r} command request sent by {str(ctx.author)!r} "
            f"({ctx.author.id!r}) with invocation {ctx.message.content!r}")

    async def on_command_completion(self, ctx: commands.Context):

        rep = None
        message_log_infos = [
            f"{ctx.command.name!r} {'slash ' if ctx.interaction else ''}"
            f"command succeeded for {str(ctx.author)!r} ({ctx.author.id!r})"]

        if ctx.interaction:
            rep = await ctx.interaction.original_response()
        else:
            async for message in ctx.history(limit=5):
                if (message.author == ctx.me
                        and message.reference
                        and message.reference.message_id == ctx.message.id):
                    rep = message
                    break
        if rep:
            message_log_infos += [" with a response"]
            if rep.content:
                short_content = sanitize(rep.content, 120)
                message_log_infos += [
                    f"starting with the text '{short_content}'"]
            for embed in rep.embeds:
                short_content = sanitize(embed.description, 120)
                message_log_infos += [
                    f"containing an embed with name {embed.title!r}, "
                    f"and with description starting with '{short_content}'"]
            for attachment in rep.attachments:
                message_log_infos += [
                    f"containing an file with name "
                    f"{attachment.filename!r} (url {attachment.url!r})"]

        _log.info(", ".join(message_log_infos))

    async def on_command_error(self, ctx, error: Exception):

        if self.extra_events.get('on_command_error', None):
            return

        if ctx.command and ctx.command.has_error_handler():
            return

        if ctx.cog and ctx.cog.has_error_handler():
            return

        await self.handle_error(ctx, error)

    async def handle_error(self, ctx: commands.Context, error: Exception) -> None:
        """
        Automatically handles the errors following the error and the context,
        and sends a message to the user with a proper message

        :param ctx: The context of the command
        :param error: The error raised
        :return: None
        """

        if isinstance(error, (commands.ConversionError, commands.BadArgument)):
            await reply_with_fallback(ctx, t("command_error.bad_argument").format(
                get_command_usage(self.command_prefix, ctx.command),
                self.command_prefix + "help " + ctx.command.name))
            _log.warning(
                f"{ctx.command.name!r} command failed for"
                f" {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Bad arguments given")
        elif isinstance(error, commands.MissingRequiredArgument):
            await reply_with_fallback(ctx, t("command_error.missing_argument").format(
                get_command_usage(self.command_prefix, ctx.command),
                self.command_prefix + "help " + ctx.command.name))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Missing required argument")
        elif (isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden)) or \
                isinstance(error, commands.BotMissingPermissions):
            await reply_with_fallback(ctx, t("command_error.bot_missing_permission"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Bot is missing permissions")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
            await reply_with_fallback(ctx, t("command_error.not_found"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"No matches for the request")
        elif isinstance(error, (commands.NotOwner, commands.MissingPermissions)):
            await reply_with_fallback(ctx, t("command_error.user_missing_permission"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"User is missing permissions")
        elif isinstance(error, commands.CommandOnCooldown):
            await reply_with_fallback(ctx, t("command_error.on_cooldown").format(error.retry_after))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"On cooldown")
        elif isinstance(error, commands.InvalidEndOfQuotedStringError):
            await reply_with_fallback(ctx, t("command_error.invalid_quoted_string"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Invalid quoted string")
        elif isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.CommandInvokeError):
            await self._log_command_error(ctx, error.original)
        else:
            _log.error(
                f"Unhandled command error{' on command ' + ctx.command.name if ctx.command else ''}\n"
                + "\n".join(f'\t{key!r}: {value!r}' for key, value in ctx.__dict__.items()),
                exc_info=error)

    async def _log_command_error(self, ctx: commands.Context, err: Exception):
        """
        Sends the internal command error to the raising channel and to the
        error channel

        :param ctx: the context of the command invocation
        :param err: the raised error
        :return: None
        """

        if isinstance(err, commands.errors.HybridCommandError):
            err = err.original.original

        error_data = tb.extract_tb(err.__traceback__)[1]
        error_filename = path.basename(error_data.filename)
        public_prompt = (
            f"File {error_filename!r}, "
            f"line {error_data.lineno}, "
            f"command {error_data.name!r}\n"
            f"{type(err).__name__} : {err}"
        )

        await reply_with_fallback(
            ctx, t("error.exception").format(public_prompt))

        data: dict[str] = {
            "Server": f"{ctx.guild.name} ({ctx.guild.id})",
            "Command": ctx.command.name,
            "Author": f"{str(ctx.author)} ({ctx.author.id})",
            "Original message": ctx.message.content,
            "Link to message": ctx.message.jump_url,
        }

        if (config.log.create_invite
                and ctx.channel.permissions_for(ctx.guild.me).create_instant_invite):
            data["Invite"] = await ctx.channel.create_invite(
                reason=t("error.invite_message"),
                max_age=604800,
                max_uses=1,
                temporary=True,
                unique=False)

        await self._log_data(
            f"{ctx.command.name!r} {'slash ' if ctx.interaction else ''}"
            f"command failed for {str(ctx.author)!r} ({ctx.author.id!r})",
            data, exc_info=(type(err), err, err.__traceback__))

    async def _log_data(
            self, message: str, data: dict, level: int = logging.ERROR,
            exc_info: Union[bool, tuple] = True) -> None:
        """
        Logs data to the console and to the log channel

        :param message: The message to log
        :param data: The contextual information to log
        :param level: The level of the log
        :param exc_info: The exception information, if any
        :return: None
        """

        if exc_info is True:
            exc_info = sys.exc_info()

        traceback = message
        data["Date"] = datetime.today().strftime(config.log.date_format)

        if exc_info:
            err_type, err_value, err_traceback = exc_info
            tb_infos = tb.extract_tb(err_traceback)[1]
            unenclosed_tb = (
                    "".join(tb.format_tb(err_traceback))
                    + "".join(tb.format_exception_only(err_type, err_value)))

            traceback = f"```\n{sanitize(unenclosed_tb, 1992)}\n```"

            data["File"] = tb_infos.filename
            data["Line"] = tb_infos.lineno
            data["Error"] = err_type.__name__
            data["Description"] = str(err_value)

        _log.log(
            level,
            (
                message + "\n"
                + "\n".join(
                    f"\t{key}: {value!r}" for key, value in data.items())
            ),
            exc_info=exc_info
        )

        if not config.log.channel:
            return

        embed = discord.Embed(title=message, color=config.color or None)
        embed.set_footer(
            text=self.user.name + (
                f" | ver. {config.version}" if config.version else ""),
            icon_url=self.user.display_avatar.url
        )

        for key, value in data.items():
            embed.add_field(name=key, value=value, inline=False)

        await self.get_channel(config.log.channel).send(traceback, embed=embed)

    async def on_error(self, event, *args, **kwargs):
        await self._log_data(
            "Error raised",
            {
                "Event": event,
                "Arguments": repr(args),
                "Keyword arguments": repr(kwargs)
            }
        )

    async def on_app_command_completion(
            self, i: discord.Interaction, command: discord.app_commands.Command):
        message_log_infos = [
            f"{command.qualified_name!r} app command succeeded for "
            f"{str(i.user.name)!r} ({i.user.id!r}) with a response"]

        rep: discord.InteractionMessage = await i.original_response()
        message_log_infos += [" with a response"]
        if rep.clean_content:
            short_content = sanitize(rep.clean_content(), 120)
            message_log_infos += [
                f"starting with the text '{short_content}'"]
        for embed in rep.embeds:
            short_content = sanitize(embed.description, 120)
            message_log_infos += [
                f"containing an embed with name {embed.title!r}, "
                f"and with description starting with '{short_content}'"]
        for attachment in rep.attachments:
            message_log_infos += [
                f"containing an file with name "
                f"{attachment.filename!r} (url {attachment.url!r})"]

        _log.info(", ".join(message_log_infos))
