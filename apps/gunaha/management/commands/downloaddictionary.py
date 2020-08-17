#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
manage.py downloaddictionary
"""

import argparse

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

private_dir = settings.DATA_DIR / "private"
assert private_dir.is_dir()


class Command(BaseCommand):
    help = "Downloads the dictionary from Google Sheets"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    def handle(self, *args, **options) -> None:
        filename = "Onespot-Sapir-Vocabulary-list-OS-Vocabulary.tsv"
        doc_id = settings.ONESPOT_GOOGLE_SHEETS_ID

        if doc_id is None:
            raise CommandError(
                "The Google Sheets ID is unset. "
                "Please set ONESPOT_GOOGLE_SHEETS_ID as an environment variable."
            )

        r = requests.get(
            f"https://docs.google.com/spreadsheets/d/{doc_id}/export",
            params={"format": "tsv"},
        )
        r.raise_for_status()

        (private_dir / filename).write_bytes(r.content)
