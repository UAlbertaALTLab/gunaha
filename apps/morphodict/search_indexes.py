#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Enables search using Haystack for models.
"""

from haystack import indexes  # type: ignore

from .models import Definition, Head


class DefinitionIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, model_attr="text")

    def get_model(self):
        return Definition

    def index_queryset(self, using=None):
        return self.get_model().objects.all()
