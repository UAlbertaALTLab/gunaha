#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import csv
import io
import logging
import re
from collections import defaultdict
from hashlib import sha384
from pathlib import Path
from typing import Dict, Set
from unicodedata import normalize

from apps.morphodict.models import Definition, DictionarySource, Head

logger = logging.getLogger(__name__)

private_dir = Path(__name__).parent.parent.parent / "run" / "private"
assert private_dir.exists()


def import_dictionary() -> None:
    logger.info("Importing Sapir OneSpot dictionary")
    filename = "Onespot-Sapir-Vocabulary-list-OS-Vocabulary.tsv"
    path_to_tsv = private_dir / filename
    assert path_to_tsv.exists()

    with open(path_to_tsv, "rb") as raw_file:
        raw_bytes = raw_file.read()

    file_hash = sha384(raw_bytes).hexdigest()
    assert len(file_hash) == 384 // 4
    tsv_file = io.StringIO(raw_bytes.decode("UTF-8"))

    logger.info("Importing %s [SHA-384: %s]", path_to_tsv, file_hash)

    # TODO: check if already imported

    starlight = DictionarySource(
        abbrv="Starlight",
        editor="Bruce Starlight",
        import_filename=filename,
        last_import_sha384=file_hash,
    )

    sapir = DictionarySource(
        abbrv="Sapir",
        editor="Edward Sapir",
        import_filename=filename,
        last_import_sha384=file_hash,
    )

    entries = csv.DictReader(tsv_file, delimiter="\t")
    terms: Dict[int, Head] = {}
    definitions: Set[Definition] = set()
    pat = re.compile(r"""^os(\d+)([abcdefgh])?$""")
    for entry in entries:
        folio_id = entry["ID"]

        # deal with duplicate ids...
        match = pat.match(folio_id)
        assert match is not None

        os_id = int(match.group(1), base=10)
        if sub_id := match.group(2):
            sub_part = 1 + ord(sub_id) - ord("a")
        else:
            sub_part = 0

        primary_key = os_id * 100 + sub_part

        term = normalize("NFC", entry["Bruce - Tsuut'ina text"])
        word_class = entry["Part of speech"]
        starlight_def = entry["Bruce - English text"]
        head = terms.setdefault(
            primary_key, Head(pk=primary_key, text=term, word_class=word_class)
        )
        if head.text and term:
            assert head.text == term, f"mismatch: {head} / {term}"
        if not head.word_class:
            head.word_class = word_class
        elif head.word_class and word_class:
            assert head.word_class == word_class, f"mismatch: {head} / {word_class}"
