#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from django.db import models

from apps.morphodict.models import Head

ONESPOT_ID_LEN = len("os00000")


class OnespotDuplicate(models.Model):
    """
    There are duplicate 'osXXXXXX' IDs in the Onespot folios. This keeps track of the
    duplicates.
    """

    entry_id = models.CharField(max_length=ONESPOT_ID_LEN, primary_key=True)
    duplicate_of = models.ForeignKey(Head, on_delete=models.CASCADE)
