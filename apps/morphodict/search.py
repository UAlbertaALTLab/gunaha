#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from functools import lru_cache
from importlib import import_module
from typing import Callable, Optional

from django.apps import apps
from django.conf import settings
from django.utils.module_loading import import_string
from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from .errors import InvalidLanguageError

DEFAULT_LANGUAGES = frozenset(("srs", "eng",))  # Tsuut'ina  # English


class HeadSearchMixin:
    """
    Defines the search() method for full-text search on Head models.
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
