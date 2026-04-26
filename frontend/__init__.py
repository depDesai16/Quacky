"""Frontend package entrypoint.

Keep import side effects minimal so package discovery and test collection
do not eagerly import the full desktop UI stack.
"""


def run_it():
    from .frontend import run_it as _run_it

    return _run_it()
