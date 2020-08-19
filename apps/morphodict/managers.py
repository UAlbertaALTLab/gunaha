#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Customize how to query certain models.
"""

from typing import Optional

from django.db import models
from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from .util import to_search_form


class HeadManager(models.Manager):
    """
    Customizes search for Head models. Adds the following convenience method:


        Head.objects.search(query) -> SearchQuerySet

    """

    def search(self, query: Optional[str]) -> SearchQuerySet:
        """
        Does a full text search based on the dictionary head.
        """

        from .models import Head

        if query is None:
            query_set = EmptySearchQuerySet()
        else:
            query_set = SearchQuerySet().models(Head)

        text = query or ""
        result_set = query_set
        result_set |= self._search_in_definition_language(text, query_set)
        result_set |= self._search_in_dictionary_language(text, query_set)

        return result_set

    def _search_in_dictionary_language(
        self, text: str, query_set: SearchQuerySet
    ) -> SearchQuerySet:
        return query_set.filter(head_simplified__startswith=to_search_form(text))

    def _search_in_definition_language(
        self, text: str, query_set: SearchQuerySet
    ) -> SearchQuerySet:
        return query_set.auto_query(text)
