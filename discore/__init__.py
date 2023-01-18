"""
Initialize the package Discore, based on the library discord.py.

Copyright (c) 2022 Kyrela
"""

from discord import *
from discord.ext.commands import *
from discord.ext.tasks import *

from .utils import *
from .bot import Bot
from .cog import Cog
