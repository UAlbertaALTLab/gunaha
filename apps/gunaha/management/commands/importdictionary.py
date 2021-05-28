#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
manage.py importdictionary
"""

import argparse

from django.core.management.base import BaseCommand, CommandError

from apps.gunaha.import_dictionary import DICTIONARY_PATH


class Command(BaseCommand):
    help = "Imports the Onespot-Sapir vocabulary list"

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
        parser.add_argument(
            "--output-json-file",
            default="Onespot-Sapir.json",
            help="Write the dictionary as JSON to this file",
        )
        parser.add_argument(
            "--input-tsv-file",
            default=DICTIONARY_PATH,
            help="Where to read the dictionary from",
        )
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--purge",
            action="store_true",
            help=(
                "Deletes ALL of the existing content imported to the database; "
                "do this only if you know what you're doing!"
            ),
        )
        group.add_argument(
            "--json-only",
            action="store_true",
            help="Don’t write to the database",
        )

    def handle(self, *args, **options) -> None:
        # Import here because I'm assuming there will be weird Django side-effects
        # otherwise :/
        from apps.gunaha.import_dictionary import (
            import_dictionary,
            DictionaryImportError,
        )

        try:
            import_dictionary(
                **{
                    k: options[k]
                    for k in (
                        "output_json_file",
                        "input_tsv_file",
                        "purge",
                        "json_only",
                    )
                }
            )
        except DictionaryImportError as error:
            raise CommandError(str(error))
