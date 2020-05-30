#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
manage.py importdictionary
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Imports the Onespot-Sapir vocabulary list"

    def handle(self, *args, **options) -> None:
        from apps.gunaha.import_dictionary import import_dictionary

        import_dictionary(purge=True)
