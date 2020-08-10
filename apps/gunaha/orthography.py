#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Deal with orthography
"""

from unicodedata import normalize


def to_search_form(query: str) -> str:
    """
    Convert a Tsuut'ina query into a searchable form.

    >>> normalize_orthography("Tłítc'ā")
    'tlitca'
    """
    with_diacritics = normalize("NFKD", normalize_orthography(query.lower()))
    return (
        with_diacritics.replace("'", "")
        .replace("’", "")
        .replace("\u0142", "l")
        .replace("\u0300", "")
        .replace("\u0301", "")
        .replace("\u0304", "")
    )


def normalize_orthography(tsuutina_word: str) -> str:
    """
    Make the orthography of Tsuut'ina words consistent.
    """
    LATIN_SMALL_LETTER_L_WITH_MIDDLE_TIDLE = "\u026B"
    LATIN_SMALL_LETTER_L_WITH_STROKE = "\u0142"

    tsuutina_word = tsuutina_word.strip()
    tsuutina_word = nfc(tsuutina_word)
    # According to Chris Cox: Original mostly used <ɫ>, but writers now prefer
    # <ł>, as it is more distinct from <t>. So let's make it consistent!
    tsuutina_word = tsuutina_word.replace(
        LATIN_SMALL_LETTER_L_WITH_MIDDLE_TIDLE, LATIN_SMALL_LETTER_L_WITH_STROKE
    )
    return tsuutina_word


def nfc(text: str) -> str:
    return normalize("NFC", text)
