import logging
from typing import Any
import traceback as tb
from os import path
import i18n
from aiohttp import ClientOSError, ServerDisconnectedError

# Import all necessary classes and functions from discord.ui.view
from discord.ui.view import View as _View
from discord.ui.view import _ViewWeights, _ViewCallback, _walk_all_components, _component_to_item
from discord import Interaction
from discord import DiscordServerError
from discord.ui.item import Item

from ..utils import config, log_data, fallback_reply

__all__ = ('View',)

_log = logging.getLogger(__name__)

class View(_View):
    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
        item_name = repr(item.label) if hasattr(item, 'label') else ""
        item_name += (f" ({item.custom_id!r})" if item_name else repr(item.custom_id)) if hasattr(item, 'custom_id') else ""
        item_name += "" if item_name else "Unknown"

        if (
                isinstance(error, ServerDisconnectedError)
                or isinstance(error, DiscordServerError)
                or isinstance(error, ClientOSError)
        ) and config.log.commands:
            _log.warning(
                f"{item_name} item interaction failed for {str(interaction.user)!r} ({interaction.user.id!r}): "
                + str(error)
            )
        else:
            error_data = tb.extract_tb(error.__traceback__)[1]
            error_filename = path.basename(error_data.filename)

            if config.log.alert_user:
                await fallback_reply(interaction, i18n.t(
                    "exception",
                    file=error_filename,
                    line=error_data.lineno,
                    function=error_data.name,
                    error=type(error).__name__,
                    error_message=error))

            user = interaction.user

            data: dict[str, str] = {
                "Server": f"{interaction.guild.name} ({interaction.guild.id})",
                "Item": item_name,
                "Author": f"{str(user)} ({user.id})",
            }

            await log_data(
                interaction.client,
                f"{item_name} item interaction failed for {str(user)!r} ({user.id!r})",
                data, logger=_log, exc_info=(type(error), error, error.__traceback__))
