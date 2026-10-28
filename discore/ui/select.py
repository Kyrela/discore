import importlib

_select = importlib.import_module('discord.ui.select')

__all__ = _select.__all__


def __getattr__(name: str):
    return getattr(_select, name)


def __dir__():
    return sorted({*globals(), *dir(_select)})
