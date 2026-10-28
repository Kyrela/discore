import discord.ui as _discord_ui
from discord.ui import *

from . import dynamic, item, modal, text_input, view
from .view import View

__all__ = [
    *(name for name in dir(_discord_ui) if not name.startswith('_')),
]


def __getattr__(name: str):
    return getattr(_discord_ui, name)


def __dir__():
    return sorted({*globals(), *dir(_discord_ui)})
