#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Customize how to query certain models.
"""

from django.db import models

from .search import HeadSearchMixin


class HeadManager(models.Manager, HeadSearchMixin):
    """
    Customizes search for Head models. Adds the following convenience method:


        Head.objects.search(query) -> SearchQuerySet

    """
