"""
The class that represent the bot's command tree
"""

import logging
import time
from typing import List, Callable

import discord.app_commands
from aiohttp import ServerDisconnectedError, ClientOSError
from i18n import t

from discord import *
from discord import app_commands
from discord._types import ClientT
from discord.app_commands import Namespace, AppCommandError

from . import ignore_cd
from .utils import get_app_command_usage, log_command_error, set_locale, config

__all__ = ('CommandTree',)

_log = logging.getLogger(__name__)


class CommandTree(app_commands.CommandTree):
    """
    A class that represents the bot's command tree.
    """
    def __init__(self, bot):
        super().__init__(bot)

    async def on_error(
            self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """|coro|

        A callback that is called when any command raises an :exc:`AppCommandError`.

        The default implementation logs the exception using the library logger,
        send the exception full context to the log channel if provided, and
        send a message to the user if configured to do so.

        To get the command that failed, :attr:`discord.Interaction.command` should
        be used.

        Parameters
        -----------
        interaction: :class:`~discord.Interaction`
            The interaction that is being handled.
        error: :exc:`AppCommandError`
            The exception that was raised.
        """

        command = interaction.command

        if command is not None and command._has_any_error_handlers():
            return

        await self.handle_error(interaction, error)

    async def handle_error(
            self, interaction: Interaction, error: app_commands.AppCommandError) -> None:
        """
        Handles an error that occurred during the execution of a command.

        :param interaction: The interaction that is being handled.
        :param error: The exception that was raised.
        """

        command = interaction.command
        logged = False

        if isinstance(error, app_commands.CommandNotFound):
            await self.sync(guild=interaction.guild)
            await interaction.response.send_message(
                t('app_error.command_not_found'), ephemeral=True)
            return

        if not isinstance(error, app_commands.CommandOnCooldown):
            await ignore_cd(interaction)

        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(t(
                'app_error.transformer',
                argument_value=error.value,
                command_usage=(get_app_command_usage(command) if command is not None else ''),
                help_command="/help " + (command.qualified_name if command else '')), ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(
                t('app_error.no_private_message'), ephemeral=True)
        elif isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message(t(
                'app_error.missing_role',
                role=error.missing_role), ephemeral=True)
        elif isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(t(
                'app_error.missing_any_role',
                roles_list=", ".join(error.missing_roles)), ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(t(
                'app_error.missing_permissions',
                permissions_list=", ".join(error.missing_permissions)), ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(t(
                'app_error.bot_missing_permissions',
                permissions_list=", ".join(error.missing_permissions)), ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(t(
                'app_error.on_cooldown',
                cooldown_time="<t:" + str(int(time.time() + error.retry_after)) + ":R>", ephemeral=True))
        elif isinstance(error, app_commands.CommandInvokeError) and (
            isinstance(error.original, ServerDisconnectedError)
            or isinstance(error.original, DiscordServerError)
            or isinstance(error.original, ClientOSError)
        ):
            logged = True
            if config.log.commands:
                _log.warning(
                    f"{command.qualified_name!r} command failed for {str(interaction.user)!r} ({interaction.user.id!r}): "
                    + str(error.original)
                )
        elif isinstance(error, app_commands.CommandInvokeError):
            logged = True
            await log_command_error(interaction, error.original, logger=_log)
        else:
            logged = True
            _log.error(
                f"{command.qualified_name!r} command failed for {str(interaction.user)!r} ({interaction.user.id!r}): "
                f"Unhandled command error\ninteraction:\n"
                + "\n".join(f'\t{attr!r}: {interaction.__getattribute__(attr)!r}' for attr in interaction.__slots__
                            if attr[0] != '_'),
                exc_info=error)

        if (not logged) and config.log.commands:
            _log.info(
                f"{command.qualified_name!r} command cancelled for {str(interaction.user)!r} ({interaction.user.id!r}): "
                + str(error))

    async def _call(self, interaction: Interaction[ClientT]) -> None:
        if not await self.interaction_check(interaction):
            interaction.command_failed = True
            return

        data: ApplicationCommandInteractionData = interaction.data  # type: ignore
        type = data.get('type', 1)
        if type != 1:
            # Context menu command...
            await self._call_context_menu(interaction, data, type)
            return

        command, options = self._get_app_command_options(data)

        # Pre-fill the cached slot to prevent re-computation
        interaction._cs_command = command

        # At this point options refers to the arguments of the command
        # and command refers to the class type we care about
        namespace = Namespace(interaction, data.get('resolved', {}), options)

        # Same pre-fill as above
        interaction._cs_namespace = namespace

        set_locale(interaction)
        self.client.dispatch('app_command', interaction, command)

        # Auto complete handles the namespace differently... so at this point this is where we decide where that is.
        if interaction.type is InteractionType.autocomplete:
            focused = next((opt['name'] for opt in options if opt.get('focused')), None)
            if focused is None:
                raise AppCommandError('This should not happen, but there is no focused element. This is a Discord bug.')

            try:
                await command._invoke_autocomplete(interaction, focused, namespace)
            except Exception:
                # Suppress exception since it can't be handled anyway.
                _log.exception('Ignoring exception in autocomplete for %r', command.qualified_name)

            return

        try:
            await command._invoke_with_namespace(interaction, namespace)
        except AppCommandError as e:
            interaction.command_failed = True
            await command._invoke_error_handlers(interaction, e)
            await self.on_error(interaction, e)
        else:
            if not interaction.command_failed:
                self.client.dispatch('app_command_completion', interaction, command)
