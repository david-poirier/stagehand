_debug = False
_print = print


def set_debug(debug):
    global _debug
    _debug = debug


def print(msg):
    if _debug:
        _print(f"\n[DEBUG] {msg}")
