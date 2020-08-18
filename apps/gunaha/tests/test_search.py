#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Try some searches
"""

import pytest


@pytest.mark.django_db
def test_search(client):
    """
    Test an ordinary search.
    """
    res = client.get("/?q=tlicha")
    assert "dog" in res.content.decode("UTF-8")


@pytest.mark.django_db
def test_query_not_found(client):
    res = client.get("?q=fhqwhgads")
    assert res.status_code == 200
    # TODO: more robust assertion
    assert "No results for" in res.content.decode("UTF-8")
