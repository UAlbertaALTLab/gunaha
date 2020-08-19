#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Try some searches
"""

from urllib.parse import urlencode

import pytest


@pytest.mark.django_db
def test_search(search_by_query):
    """
    Test an ordinary search.
    """
    query = "tlicha"
    res = search_by_query(query)
    assert "dog" in res.content.decode("UTF-8")


@pytest.mark.django_db
def test_query_not_found(search_by_query):
    non_word = "fhqwhgads"
    res = search_by_query(non_word)
    assert res.status_code == 200
    # TODO: more robust assertion
    assert "No results for" in res.content.decode("UTF-8")


@pytest.fixture
def search_by_query(client):
    """
    Helper to make searching by query faster:

        search_by_query(query: str, **additional_query_args) -> HttpResponse

    """

    def search(query, **kwargs):
        kwargs.update(q=query)
        res = client.get("/?" + urlencode(kwargs))
        return res

    return search
