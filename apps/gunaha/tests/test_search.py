#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Try some searches
"""

import pytest


@pytest.mark.django_db
def test_search(client):
    res = client.get("/?q=tlicha")
    assert "dog" in res.content.decode("UTF-8")
