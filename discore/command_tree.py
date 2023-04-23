"""
The class that represent the bot's command tree
"""

import logging

from discord import *
from discord import app_commands

from .utils import t, get_app_command_usage, log_command_error

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

        if isinstance(error, app_commands.TransformerError):
            await interaction.response.send_message(t(
                interaction, 'app_error.transformer',
                argument_value=error.value,
                command_usage=(get_app_command_usage(command) if command is not None else ''),
                help_command="/help " + (command.qualified_name if command else '')), ephemeral=True)
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message(
                t(interaction, 'app_error.no_private_message'), ephemeral=True)
        elif isinstance(error, app_commands.MissingRole):
            await interaction.response.send_message(t(
                interaction, 'app_error.missing_role',
                role=error.missing_role), ephemeral=True)
        elif isinstance(error, app_commands.MissingAnyRole):
            await interaction.response.send_message(t(
                interaction, 'app_error.missing_any_role',
                roles_list=", ".join(error.missing_roles)), ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(t(
                interaction, 'app_error.missing_permissions',
                permissions_list=", ".join(error.missing_permissions)), ephemeral=True)
        elif isinstance(error, app_commands.BotMissingPermissions):
            await interaction.response.send_message(t(
                interaction, 'app_error.bot_missing_permissions',
                permissions_list=", ".join(error.missing_permissions)), ephemeral=True)
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(t(
                interaction, 'app_error.cooldown',
                cooldown_time=abs(error.retry_after)), ephemeral=True)
        elif isinstance(error, app_commands.CommandNotFound):
            await self.sync(guild=interaction.guild)
            await interaction.response.send_message(
                t(interaction, 'app_error.command_not_found'), ephemeral=True)
        elif isinstance(error, app_commands.CommandInvokeError):
            await log_command_error(self.client, interaction, error.original, logger=_log)
        else:
            _log.error(
                f"Unhandled command error{' on command ' + command.qualified_name if command else ''}\n"
                + "\n".join(f'\t{attr!r}: {interaction.__getattribute__(attr)!r}' for attr in interaction.__slots__
                            if attr[0] != '_'),
                exc_info=error)
