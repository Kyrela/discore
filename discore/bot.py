"""
The class representing the Discord bot
"""

import asyncio
import os
from os import path
import logging
import datetime
from importlib.metadata import version
from i18n import t

from discord.ext import commands
import discord

from .help import EmbedHelpCommand
from .tree import CommandTree
from .utils import (config, config_init, logging_init, i18n_init, set_locale, sanitize,
                    fallback_reply, get_command_usage, log_command_error, log_data)

__all__ = ('Bot',)

_log = logging.getLogger(__name__)


class NoSpecifiedTokenError(Exception):
    """
    a basic custom error, in case no token is specified
    """
    pass


class Bot(commands.Bot):
    """
    The class representing the Discord bot
    """

    def __init__(self, command_prefix: str = None, **kwargs):
        """
        Initialize the bot

        :param configuration_file: the toml file containing configuration information
        """

        self.start_time = None
        self.initialisation_time = datetime.datetime.now()

        config_init(**kwargs)
        logging_init(**kwargs)
        i18n_init(**kwargs)
        _log.info(f"Bot initialising... discore v{version('discore')}, discord.py v{version('discord.py')}")

        super().__init__(
            command_prefix=command_prefix or config.prefix,
            description=kwargs.pop('description', config.description) or None,
            intents=kwargs.pop('intents', discord.Intents.all()),
            help_command=kwargs.pop('help_command', EmbedHelpCommand(command_attrs=config.help)),
            tree_cls=kwargs.pop('tree_cls', CommandTree),
            **kwargs
        )

        asyncio.run(self._load_cogs())

    async def _load_cogs(self):
        """
        loads dynamically the cogs found in the /cog folder and the log cog
        """

        help_cog_name = config.help.cog.title() if config.help.cog else None

        if path.isdir("cogs"):
            for file in os.listdir("cogs"):

                if not file.endswith(".py"):
                    continue

                cog_name = file[:-3].title()
                cog_class = getattr(__import__('cogs.' + cog_name.lower(), fromlist=[cog_name]), cog_name)
                new_cog = cog_class(self)
                await self.add_cog(new_cog)

                if help_cog_name == cog_name:
                    self.help_command.cog = new_cog
                _log.info(f"Cog {cog_name!r} loaded")

        if help_cog_name and not self.help_command.cog:
            raise ModuleNotFoundError(
                f"The cog {help_cog_name!r}, required by the help command, wasn't found")

    def run(self, token=None, **kwargs):
        """
        Runs the bot

        :return: None
        """

        token = token or config.token or None

        if not token:
            raise NoSpecifiedTokenError(
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
        self.start_time = datetime.datetime.now()
        if self.application_id:
            sync_res = await self.tree.sync()
            if sync_res is None:
                _log.error("Failed to sync the tree")
            elif sync_res:
                _log.info(f"Slash commands successfully synced: {', '.join([c.name for c in sync_res])}")
            else:
                _log.info("No slash commands to sync")
        _log.info(f"Bot launched in {(self.start_time - self.initialisation_time).total_seconds():.3f}s,"
                  f" ready to use (prefix {self.command_prefix!r})")

    async def on_guild_join(self, guild: discord.Guild):
        if self.application_id:
            await self.tree.sync(guild=guild)

    async def on_disconnect(self):
        _log.warning(f"Bot disconnected")

    async def on_resumed(self):
        _log.info("Bot resumed")

    async def invoke(self, ctx: commands.Context, /) -> None:
        if ctx.command is not None:
            self.dispatch('command', ctx)
            set_locale(ctx)
            try:
                if await self.can_run(ctx, call_once=True):
                    await ctx.command.invoke(ctx)
                else:
                    raise commands.errors.CheckFailure('The global check once functions failed.')
            except commands.errors.CommandError as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch('command_completion', ctx)
        elif ctx.invoked_with:
            exc = commands.errors.CommandNotFound(f'Command "{ctx.invoked_with}" is not found')
            self.dispatch('command_error', ctx, exc)

    async def on_command(self, ctx: commands.Context):
        if ctx.interaction:
            return

        _log.info(
            f"{ctx.command.name!r} command request sent by {str(ctx.author)!r} "
            f"({ctx.author.id!r}) with invocation {ctx.message.content!r}")

    async def on_command_completion(self, ctx: commands.Context):

        if ctx.interaction:
            return

        rep = None
        message_log_infos = [
            f"{ctx.command.name!r} command succeeded for {str(ctx.author)!r}"
            f" ({ctx.author.id!r})"]

        async for message in ctx.history(limit=5):
            if (message.author == ctx.me
                    and message.reference
                    and message.reference.message_id == ctx.message.id):
                rep = message
                break

        if rep:
            message_log_infos.append("with a response")
            if rep.content:
                short_content = sanitize(rep.content, 120)
                message_log_infos += [
                    f"starting with the text '{short_content}'"]
            for embed in rep.embeds:
                message_log_infos += [
                    f"containing an embed with name {embed.title!r}"]
                if embed.description:
                    short_content = sanitize(embed.description, 120)
                    message_log_infos += [
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

        if isinstance(error, commands.HybridCommandError):
            error = error.original

        if isinstance(error, (commands.ConversionError, commands.BadArgument)):
            await fallback_reply(ctx, t(
                "command_error.bad_argument",
                command_usage=get_command_usage(self.command_prefix, ctx.command),
                help_command=self.command_prefix + "help " + ctx.command.name))
            _log.warning(
                f"{ctx.command.name!r} command failed for"
                f" {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Bad arguments given")
        elif isinstance(error, commands.MissingRequiredArgument):
            await fallback_reply(ctx, t(
                "command_error.missing_argument",
                command_usage=get_command_usage(self.command_prefix, ctx.command),
                help_command=self.command_prefix + "help " + ctx.command.name))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Missing required argument")
        elif (isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.Forbidden)) or \
                isinstance(error, commands.BotMissingPermissions):
            await fallback_reply(ctx, t("command_error.bot_missing_permission"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Bot is missing permissions")
        elif isinstance(error, commands.CommandInvokeError) and isinstance(error.original, discord.NotFound):
            await fallback_reply(ctx, t("command_error.not_found"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"No matches for the request")
        elif isinstance(error, (commands.NotOwner, commands.MissingPermissions)):
            await fallback_reply(ctx, t("command_error.user_missing_permission"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"User is missing permissions")
        elif isinstance(error, commands.CommandOnCooldown):
            await fallback_reply(ctx, t("command_error.on_cooldown", cooldown_time=int(error.retry_after)))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"On cooldown")
        elif isinstance(error, commands.InvalidEndOfQuotedStringError):
            await fallback_reply(ctx, t("command_error.invalid_quoted_string"))
            _log.warning(
                f"{ctx.command.name!r} command failed for {str(ctx.author)!r} ({ctx.author.id!r}): "
                f"Invalid quoted string")
        elif isinstance(error, commands.CommandNotFound):
            return
        elif (isinstance(error, commands.CommandInvokeError)
              or isinstance(error, discord.app_commands.CommandInvokeError)):
            await log_command_error(self, ctx, error.original, logger=_log)
        else:
            _log.error(
                f"Unhandled command error{' on command ' + ctx.command.name if ctx.command else ''}\n"
                + "\n".join(f'\t{key!r}: {value!r}' for key, value in ctx.__dict__.items()),
                exc_info=error)

    async def on_error(self, event, *args, **kwargs):
        await log_data(
            self,
            "Error raised",
            {
                "Event": event,
                "Arguments": repr(args),
                "Keyword arguments": repr(kwargs)
            },
            logger=_log
        )

    async def on_app_command_completion(
            self, i: discord.Interaction, command: discord.app_commands.Command) -> None:
        """
        Logs the completion of an app command

        :param i: The interaction
        :param command: The command that was completed
        :return: None
        """

        message_log_infos = [
            f"{command.qualified_name!r} app command succeeded for "
            f"{str(i.user)!r} ({i.user.id!r})"]

        rep: discord.InteractionMessage = await i.original_response()
        message_log_infos.append("with a response")
        if rep.clean_content:
            short_content = sanitize(rep.clean_content, 120)
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

    async def on_app_command(
            self, i: discord.Interaction, command: discord.app_commands.Command) -> None:
        args = await i.command._transform_arguments(i, i._cs_namespace)
        _log.info(
            f"{i.command.name!r} app command request sent by {str(i.user)!r} "
            f"({i.user.id!r}) with invocation \"{args!r}\"")
