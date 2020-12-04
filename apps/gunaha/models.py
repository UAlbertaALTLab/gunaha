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

    entry_id = models.CharField(
        max_length=ONESPOT_ID_LEN,
        primary_key=True,
        help_text="Onespot ID of the duplicate entry",
    )
    duplicate_of = models.ForeignKey(
        Head, on_delete=models.CASCADE, help_text="The entry that is a duplicate of."
    )

    def __str__(self) -> str:
        return f"{self.entry_id} → {self.duplicate_of.pk}"


class Recording(models.Model):
    """
    A recording of Bruce saying a particular word.
    """

    entry = models.ForeignKey(
        Head, on_delete=models.CASCADE, help_text="entry that this is a recording of"
    )
    compressed_audio = models.FileField(upload_to="recordings")

    def __str__(self) -> str:
        return f"🔊 “{self.entry.text}”"
