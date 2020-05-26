#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import csv
import io
import logging
import re
from collections import defaultdict
from hashlib import sha1, sha384
from pathlib import Path
from typing import Dict, Set, Tuple
from unicodedata import normalize

from django.db import transaction

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

    # Check if already imported
    try:
        ds = DictionarySource.objects.get(abbrv="Starlight")
    except DictionarySource.DoesNotExist:
        logger.info("Importing for the first time!")
    else:
        if ds.last_import_sha384 == file_hash:
            logger.info("Already imported %s; skipping...", path_to_tsv)
            return

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

    Definition2Source = Definition.citations.through

    heads: Dict[int, Head] = {}
    definitions: Dict[int, Definition] = {}
    mappings: Set[Tuple[int, int]] = set()

    entries = csv.DictReader(tsv_file, delimiter="\t")
    for entry in entries:
        folio_id = entry["ID"]

        term = nfc(entry["Bruce - Tsuut'ina text"])
        word_class = entry["Part of speech"]

        primary_key = make_primary_key(term, word_class)
        head = heads.setdefault(
            primary_key, Head(pk=primary_key, text=term, word_class=word_class)
        )

        starlight_def = nfc(entry["Bruce - English text"])
        if starlight_def:
            pk = make_primary_key(starlight_def, str(head.pk))
            dfn = Definition(pk=pk, text=starlight_def, defines=head)
            definitions[pk] = dfn
            mappings.add((pk, starlight.pk))

        sapir_def = nfc(entry["Sapir - English transcription"])
        if sapir_def:
            pk = make_primary_key(sapir_def, str(head.pk))
            dfn = Definition(pk=pk, text=sapir_def, defines=head)
            definitions[pk] = dfn
            mappings.add((pk, sapir.pk))

    logger.info(
        "will insert: heads: %d, defs: %d", len(heads), len(definitions),
    )

    with transaction.atomic():
        DictionarySource.objects.bulk_create([starlight, sapir])
        Head.objects.bulk_create(heads.values())
        Definition.objects.bulk_create(definitions.values())
        Definition2Source.objects.bulk_create(
            Definition2Source(definition_id=def_pk, dictionarysource_id=dict_pk)
            for def_pk, dict_pk in mappings
        )

    logger.info("Done importing from %s", path_to_tsv)


def nfc(text: str) -> str:
    return normalize("NFC", text)


def make_primary_key(*args: str) -> int:
    number = int(sha1("\n".join(args).encode("UTF-8")).hexdigest(), base=16)
    return number & 0xFFFFFFFF
