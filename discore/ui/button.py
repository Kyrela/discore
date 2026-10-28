import importlib

_button = importlib.import_module('discord.ui.button')

__all__ = _button.__all__


def __getattr__(name: str):
    return getattr(_button, name)


def __dir__():
    return sorted({*globals(), *dir(_button)})
