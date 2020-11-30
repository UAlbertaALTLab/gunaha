#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import pytest

from apps.gunaha.models import OnespotDuplicate
from apps.morphodict.models import Head


@pytest.mark.django_db
def test_duplicate():
    original = Head(entry_id="os00029", text="sinághà", word_class="Noun")
    original.save()

    duplicate = OnespotDuplicate(
        entry_id="os00049", duplicate_of=Head.objects.get(entry_id="os00029")
    )
    duplicate.save()

    assert duplicate.duplicate_of == original
