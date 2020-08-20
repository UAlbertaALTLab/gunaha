#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from functools import lru_cache
from importlib import import_module
from typing import Callable

from django.conf import settings
from django.utils.module_loading import import_string


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
    _to_search_form = import_string(settings.MORPHODICT_TOKEN_TO_SEARCH_FORM)
    term = _to_search_form(query)
    if not isinstance(term, str):
        raise TypeError(f"returns non-string")
    return term
