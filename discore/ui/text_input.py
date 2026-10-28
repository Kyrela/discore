import importlib

_text_input = importlib.import_module('discord.ui.text_input')

__all__ = _text_input.__all__


def __getattr__(name: str):
    return getattr(_text_input, name)


def __dir__():
    return sorted({*globals(), *dir(_text_input)})
