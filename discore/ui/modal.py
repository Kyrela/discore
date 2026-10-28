import importlib

_modal = importlib.import_module('discord.ui.modal')

__all__ = _modal.__all__


def __getattr__(name: str):
    return getattr(_modal, name)


def __dir__():
    return sorted({*globals(), *dir(_modal)})
