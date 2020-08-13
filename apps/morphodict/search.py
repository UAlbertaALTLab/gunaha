#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Search utilties.
"""

from typing import Optional

from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from apps.gunaha.orthography import to_search_form

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
