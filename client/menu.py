# coding: utf-8
"""Shared in-game MODS menu API 1 adapter."""
import evejs_mod_menu as _ae_mods
import __builtin__ as _ae_builtins


def _ae_owner():
    return getattr(_ae_builtins, '_evejs_asteroid_erosion_v1', None)


def available():
    owner = _ae_owner()
    return owner is not None and owner.usable()


def open_window():
    owner = _ae_owner()
    if owner is not None and owner.usable():
        owner.open_window()


registration = _ae_mods.register('asteroid-erosion', {'en': u'Asteroid Erosion'},
                                 open_window, is_available=available, api_version=1)


def cleanup():
    registration.close()
    owner = _ae_owner()
    if owner is not None:
        owner.close_window()
