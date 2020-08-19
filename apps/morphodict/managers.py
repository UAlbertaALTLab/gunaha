#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from typing import Optional

from django.db import models


class HeadManager(models.Manager):
    def search(self, query: Optional[str]):
        # Import .search here to prevent an import cycle
        from .search import search_entries

        return search_entries(query)
