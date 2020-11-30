#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
manage.py importrecordings
"""

import argparse
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Imports recordings from onespot-recordings.sqlite3"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        pass

    def handle(self, *args, **options) -> None:
        from apps.gunaha.import_recordings import import_recordings

        database_path = (
            Path(settings.DATA_DIR) / "private" / "onespot-recordings.sqlite3"
        )
        if not database_path.exists():
            raise CommandError(f"could not find database: {database_path}")
        import_recordings(os.fspath(database_path))
