#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Try some searches
"""

from urllib.parse import urlencode

import pytest
from django.utils.html import escape as escape_html
from pytest_django.asserts import assertInHTML  # type: ignore


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query,tsuutina,english",
    [
        ("tlicha", "tłích'ā", "dog"),
        ("dog", "dóghà", "whiskers"),
        ("sigunaha", "sīgūnáhà", "my word"),
    ],
)
def test_search(query, tsuutina, english, search_by_query):
    """
    Test an ordinary search.
    """
    res = search_by_query(query)
    page = res.content.decode("UTF-8")
    assertInHTML(f"<li> {escape_html(english)}", page)
    print(page)
    assertInHTML(f'<dfn lang="srs">{escape_html(tsuutina)}', page)


@pytest.mark.django_db
def test_query_not_found(search_by_query):
    non_word = "fhqwhgads"
    res = search_by_query(non_word)
    assert res.status_code == 200
    # TODO: more robust assertion
    assert "No results for" in res.content.decode("UTF-8")


def test_search_in_tsuutina_only(search_by_query):
    query = "dog"
    tsuutina = "dóghà"
    correct_definition = "whiskers"
    incorrect_definition = "dog"

    res = search_by_query(query, lang="srs")
    page = res.content.decode("UTF-8")

    assertInHTML(f'<dfn lang="srs"> {escape_html(tsuutina)}', page)
    assertInHTML(f"<li> {escape_html(correct_definition)}", page)
    assertInHTML(f"<li> {escape_html(incorrect_definition)}", page, count=0)


def test_search_in_english_only(search_by_query):
    query = "dog"
    tsuutina = "tłích'ā"
    correct_definition = "dog"
    incorrect_definition = "whiskers"

    res = search_by_query(query, lang="eng")
    page = res.content.decode("UTF-8")

    assertInHTML(f'<dfn lang="srs"> {escape_html(tsuutina)}', page)
    assertInHTML(f"<li> {escape_html(correct_definition)}", page)
    assertInHTML(f"<li> {escape_html(incorrect_definition)}", page, count=0)


def test_search_empty_lang(search_by_query):
    query = "dog"

    res = search_by_query(query, lang="")
    page = res.content.decode("UTF-8")

    tsuutina = "tłích'ā"
    assertInHTML(f'<dfn lang="srs"> {escape_html(tsuutina)}', page)

    tsuutina = "dóghà"
    assertInHTML(f'<dfn lang="srs"> {escape_html(tsuutina)}', page)


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
