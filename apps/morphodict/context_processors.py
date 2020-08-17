#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Context processors -- augments the context appropriately.
"""

from django.conf import settings
from django.http import HttpRequest


def site_info(request: HttpRequest) -> dict:
    """
    Adds basic site info to the context like:

        {{ sitename }} -- MORPHODICT_SITE_NAME
        {{ langname }} -- MORPHODICT_LANGUAGE_NAME
    """

    context = {}

    if hasattr(settings, "MORPHODICT_SITE_NAME"):
        context["sitename"] = settings.MORPHODICT_SITE_NAME

    if hasattr(settings, "MORPHODICT_LANGUAGE_NAME"):
        context["langname"] = settings.MORPHODICT_LANGUAGE_NAME

    return context
