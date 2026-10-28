import importlib

_item = importlib.import_module('discord.ui.item')

__all__ = _item.__all__


def __getattr__(name: str):
    return getattr(_item, name)


def __dir__():
    return sorted({*globals(), *dir(_item)})
