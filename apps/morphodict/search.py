#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Search utilties.
"""

from importlib import import_module
from typing import Optional

from django.conf import settings
from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from .models import Head


def search_entries(query: Optional[str]):
    """
    Results are ALWAYS ordered!
    """

    if query is None:
        query_set = EmptySearchQuerySet()
    else:
        query_set = SearchQuerySet().models(Head)

    text = query or ""
    return query_set.auto_query(text) | query_set.filter(
        head__startswith=to_search_form(text)
    )


def to_search_form(query: str) -> str:
    *module_path, callable_name = settings.MORPHODICT_TOKEN_TO_SEARCH_FORM.split(".")
    mod = import_module(".".join(module_path))
    fn = getattr(mod, callable_name)
    assert callable(fn), f"{settings.MORPHODICT_TOKEN_TO_SEARCH_FORM} is not callable"
    term = fn(query)
    if not isinstance(term, str):
        raise TypeError(f"returns non-string")
    return term
