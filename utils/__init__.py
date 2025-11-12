from importlib import import_module
import sys as _sys

_module = import_module("bot.utils")
_sys.modules[__name__] = _module

