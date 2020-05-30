#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    def handle(self, *args, **options) -> None:
        from apps.gunaha.import_dictionary import import_dictionary

        import_dictionary()
