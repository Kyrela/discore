"""
Initialize the package Discore, based on the library discord.py.

Copyright (c) 2022-2023 Kyrela
"""

from . import ui as _ui

from discord import *
from discord import app_commands
from discord.ext.commands import *
from discord.ext.tasks import *

from .utils import *
from .bot import Bot, get_bot
from .cog import Cog

globals()['ui'] = _ui

__version__ = "0.10"
__version_info__ = (0, 10)
__copyright__ = "Copyright 2022-2025"
__author__ = "Kyrela"
__license__ = "MIT"
__name__ = "Discore"
__description__ = \
    "A core for initialise, run and tracks errors of discord.py bots"
__url__ = "https://github.com/kyrela/discore"
