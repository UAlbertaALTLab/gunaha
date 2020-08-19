#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Search utilties.
"""

from typing import Optional

from django.conf import settings
from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from .models import Head
from .util import get_function


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
        head_simplified__startswith=to_search_form(text)
    )


def to_search_form(query: str) -> str:
    term = get_function(settings.MORPHODICT_TOKEN_TO_SEARCH_FORM)(query)
    if not isinstance(term, str):
        raise TypeError(f"returns non-string")
    return term
