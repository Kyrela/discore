"""
The class representing the Discord bot
"""

import asyncio
import os
import sys
from os import path
import logging
import time
from textwrap import shorten
from i18n import t
from datetime import datetime
import traceback as tb

from discord.ext import commands
import discord

from .help import EmbedHelpCommand
from .utils import (
    init_config, setup_logging, get_config,
    reply_with_fallback, get_command_usage)

__all__ = ('Bot', 'config')

config = get_config()

_log = logging.getLogger(__name__.split(".")[0])


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
        _log = logging.getLogger(__name__.split(".")[0])
        _log.info("Bot initialising...")

        super().__init__(
            command_prefix=command_prefix or config.prefix,
            description=kwargs.pop('description', config.description) or None,
            intents=kwargs.pop('intents', discord.Intents.all()),
            help_command=kwargs.pop('help_command', EmbedHelpCommand(command_attrs=config.help.meta)),
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
            f"Connected to Discord as {self.user.name!r}"
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
        _log.info(
            f"{ctx.command.name!r} command request sent by {str(ctx.author)!r} "
            f"({ctx.author.id!r}) with invocation "
            f"{ctx.message.content[len(self.command_prefix):]!r}")

    async def on_command_completion(self, ctx: commands.Context):
        rep = None
        message_log_infos = []
        async for message in ctx.history(limit=5):
            if (message.author == ctx.me
                    and message.reference
                    and message.reference.message_id == ctx.message.id):
                rep = message
                break
        if rep:
            message_log_infos += [" with a response"]
            if rep.content:
                short_content = shorten(
                    repr(rep.content)[1:-1], width=120, placeholder='...')
                message_log_infos += [
                    f"starting with the text '{short_content}'"]
            for embed in rep.embeds:
                short_content = shorten(
                    repr(embed.description)[1:-1], width=120, placeholder='...')
                message_log_infos += [
                    f"containing an embed with name {embed.title!r}, "
                    f"and with description starting with '{short_content}'"]
            for attachment in rep.attachments:
                message_log_infos += [
                    f"containing an file with name "
                    f"{attachment.filename!r} (url {attachment.url!r})"]

        _log.info(
            f"{ctx.command.name!r} command succeeded for {str(ctx.author)!r} "
            f"({ctx.author.id!r})"
            + ", ".join(message_log_infos))

    async def on_command_error(self, ctx, error: Exception):
        if (isinstance(error, commands.ConversionError)
                or isinstance(error, commands.BadArgument)):
            await reply_with_fallback(ctx, t("error.bad_argument").format(
                get_command_usage(self.command_prefix, ctx.command),
                self.command_prefix + "help " + ctx.command.name))
            _log.warning(
                f"{ctx.command.name!r} command failed for"
                f" {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Bad arguments given")
        elif isinstance(error, commands.MissingRequiredArgument):
            await reply_with_fallback(ctx, t("error.missing_argument").format(
                get_command_usage(self.command_prefix, ctx.command),
                self.command_prefix + "help " + ctx.command.name))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Missing required argument")
        elif (isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden)) or \
                isinstance(error, commands.BotMissingPermissions):
            await reply_with_fallback(ctx, t("error.bot.missing_permission"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Bot is missing permissions")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
            await reply_with_fallback(ctx, t("error.not_found"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"No matches for the request")
        elif isinstance(error, commands.NotOwner) or isinstance(error, commands.NotOwner) or \
                isinstance(error, commands.MissingPermissions):
            await reply_with_fallback(ctx, t("error.user.missing_permission"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"User is missing permissions")
        elif isinstance(error, commands.CommandOnCooldown):
            await reply_with_fallback(ctx, t("error.on_cooldown").format(error.retry_after))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"On cooldown")
        elif isinstance(error, commands.InvalidEndOfQuotedStringError):
            await reply_with_fallback(ctx, t("error.invalid_quoted_string"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Invalid quoted string")
        elif not isinstance(error, commands.CommandNotFound):
            if isinstance(error, commands.CommandInvokeError):
                error = error.original
            await self._command_error(ctx, error)

    async def _command_error(self, ctx: commands.Context, err: Exception):
        """
        Sends the internal command error to the raising channel and to the error channel

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
            f"command {repr(error_data.name)}\n"
            f"{err.__class__.__name__} : {err}"
        )

        await reply_with_fallback(ctx, t("error.exception").format(public_prompt))

        if (ctx.guild.me.guild_permissions.manage_guild
                and await ctx.guild.invites()):
            invite = (await ctx.guild.invites())[0].url
        elif (ctx.channel.permissions_for(ctx.guild.me).create_instant_invite
                and config.log.create_invite):
            invite = await ctx.channel.create_invite(
                reason=t("error.invite_message"),
                max_age=86400,
                max_uses=1,
                temporary=True,
                unique=False
            )
        else:
            invite = None

        _log.error(
            f"{repr(ctx.command.name)} command failed for "
            f"{repr(str(ctx.author))} ({repr(ctx.author.id)})\n"
            f"\tDate: {datetime.today().strftime(config.log.date_format)}\n"
            f"\tServer: {ctx.guild.name} ({ctx.guild.id})\n"
            f"\tCommand: {error_data.name}\n"
            f"\tAuthor: {str(ctx.author)} ({ctx.author.id})\n"
            f"\tFile: {error_data.filename}\n"
            f"\tLine: {error_data.lineno}\n"
            f"\tError: {err.__class__.__name__}\n"
            f"\tDescription: {str(err)}\n"
            f"\tOriginal message: {ctx.message.content}\n"
            f"\tLink to message: {ctx.message.jump_url}" +
            (f"\n\tLink to server: {invite}" if invite else ""),
            exc_info=err
        )

        if config.log.channel:
            embed = discord.Embed(
                title="Bug raised", color=config.color or None)
            embed.set_footer(
                text=self.user.name + (
                    f" | ver. {config.version}" if config.version else ""),
                icon_url=self.user.display_avatar.url
            )
            embed.add_field(name="Date", value=datetime.today().strftime(
                config.log.date_format))
            embed.add_field(name="Server",
                            value=f"{ctx.guild.name} ({ctx.guild.id})")
            embed.add_field(name="Command", value=error_data.name)
            embed.add_field(name="Author",
                            value=f"{str(ctx.author)} ({ctx.author.id})")
            embed.add_field(name="File", value=error_data.filename)
            embed.add_field(name="Line", value=str(error_data.lineno))
            embed.add_field(name="Error", value=type(err).__name__)
            embed.add_field(name="Description", value=str(err))
            embed.add_field(name="Original message", value=ctx.message.content)
            embed.add_field(name="Link to message", value=ctx.message.jump_url)
            if invite:
                embed.add_field(name="Link to server", value=invite)

            traceback = "".join(tb.format_tb(err.__traceback__)).replace("```", "'''")
            await self.get_channel(config.log.channel).send(
                f"```\n{traceback}\n```", embed=embed)

    async def on_error(self, event, *args, **kwargs):
        err_type, err_value, err_traceback = sys.exc_info()
        tb_infos = tb.extract_tb(err_traceback)[1]
        traceback = "".join(tb.format_tb(err_traceback)).replace("```", "'''")
        _log.error(
            f"Error raised\n"
            f"\targs: {repr(args)}\n"
            f"\tkargs: {repr(kwargs)}",
            exc_info=err_value)
        if config.log.channel:
            embed = discord.Embed(title="Bug raised")
            embed.set_footer(
                text=self.user.name + (
                    f" | ver. {config.version}" if config.version else ""),
                icon_url=self.user.display_avatar.url
            )
            embed.add_field(name="Date", value=datetime.today().strftime(
                config.log.date_format))
            embed.add_field(name="Event", value=event)
            embed.add_field(name="File", value=tb_infos.filename)
            embed.add_field(
                name="Line", value=str(tb_infos.lineno))
            embed.add_field(name="Error", value=err_type.__name__)
            embed.add_field(name="Description", value=str(err_value))
            embed.add_field(name="Arguments", value=f"{args!r}\n\n{kwargs!r}")
            await self.get_channel(config.log.channel).send(
                f"```\n{traceback}\n```", embed=embed)
