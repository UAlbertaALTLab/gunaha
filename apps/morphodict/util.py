#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from functools import lru_cache
from importlib import import_module
from typing import Callable

from django.conf import settings


@lru_cache
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


def to_search_form(query: str) -> str:
    """
    Turns the query into a "searchable" form. This usually means removing diacritics,
    removing punctuation, and generaly normalizing text. The rules vary by language, so
    this is configurable using the setting::

        MORPHODICT_TOKEN_TO_SEARCH_FORM

    This is called during indexing to index the heads into a searchable form,
    and again, by the Head.objects.search() when searching for a term in the dictionary
    language.
    """
    term = get_function(settings.MORPHODICT_TOKEN_TO_SEARCH_FORM)(query)
    if not isinstance(term, str):
        raise TypeError(f"returns non-string")
    return term
