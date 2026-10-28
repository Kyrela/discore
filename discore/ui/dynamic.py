import importlib

_dynamic = importlib.import_module('discord.ui.dynamic')

__all__ = _dynamic.__all__


def __getattr__(name: str):
    return getattr(_dynamic, name)


def __dir__():
    return sorted({*globals(), *dir(_dynamic)})
