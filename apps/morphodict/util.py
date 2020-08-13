#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from importlib import import_module
from typing import Callable


def get_function(path: str) -> Callable:
    """
    Gets a function from a given path.
    """
    *module_path, callable_name = path.split(".")
    module = import_module(".".join(module_path))
    fn = getattr(module, callable_name)

    if not callable(fn):
        raise ValueError(f"{path} is not callable")

    return fn
