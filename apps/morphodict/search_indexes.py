#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Enables search using Haystack for models.
"""

from haystack import indexes  # type: ignore

from .models import Definition, Head


class HeadIndex(indexes.SearchIndex, indexes.Indexable):
    # See: ./apps/morphodict/templates/search/indexes/morphodict/head_text.txt
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return Head

    def index_queryset(self, using=None):
        return self.get_model().objects.all().prefetch_related("definitions")
