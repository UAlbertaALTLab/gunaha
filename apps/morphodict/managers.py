#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Customize how to query certain models.
"""

from typing import Optional

from django.apps import apps
from django.db import models
from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from .apps import MorphoDictConfig
from .errors import InvalidLanguageError
from .util import to_search_form

DEFAULT_LANGUAGES = frozenset(("srs", "eng",))  # Tsuut'ina  # English


class HeadManager(models.Manager):
    """
    Customizes search for Head models. Adds the following convenience method:


        Head.objects.search(query) -> SearchQuerySet

    """

    def search(self, query: Optional[str], languages=None) -> SearchQuerySet:
        """
        Does a full text search based on the dictionary head.
        """

        if not languages:
            languages = DEFAULT_LANGUAGES
        elif len(DEFAULT_LANGUAGES.intersection(languages)) == 0:
            # Cannot search for invalid languages
            raise InvalidLanguageError(languages)

        if query is None:
            query_set = EmptySearchQuerySet()
        else:
            query_set = SearchQuerySet().models(self.get_model())

        text = query or ""
        result_set = query_set
        if "eng" in languages:
            result_set |= self._search_in_definition_language(text, query_set)
        if "srs" in languages:
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

    def get_model(self):
        """
        We cannot import the Head model directly (or even reference it by name!) or else
        mypy v0.770 gets VERY upset (possible import cycle?); instead, do this to return
        the model class:
        """
        return apps.get_model("morphodict.Head")
