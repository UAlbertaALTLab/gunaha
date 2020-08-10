#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Deal with orthography
"""

from unicodedata import normalize


def normalize_orthography(tsuutina_word: str) -> str:
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
