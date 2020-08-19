#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Search utilties.
"""

from typing import Optional

from django.conf import settings

from .util import get_function


def to_search_form(query: str) -> str:
    term = get_function(settings.MORPHODICT_TOKEN_TO_SEARCH_FORM)(query)
    if not isinstance(term, str):
        raise TypeError(f"returns non-string")
    return term
