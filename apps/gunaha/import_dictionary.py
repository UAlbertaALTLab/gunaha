#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import csv
import io
import logging
from hashlib import sha384
from pathlib import Path
from typing import List
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
    terms: List[Head] = []
    for entry in entries:
        folio_id = entry["ID"]
        assert folio_id.startswith("os")  # for "Onespot"
        # deal with duplicate ids...
        primary_key = int(folio_id[2:], base=10)
        term = normalize("NFC", entry["Bruce - Tsuut'ina text"])
        word_class = entry["Part of speech"]
        starlight_def = entry["Bruce - English text"]
        terms.append(Head(pk=primary_key, text=term, word_class=word_class))
