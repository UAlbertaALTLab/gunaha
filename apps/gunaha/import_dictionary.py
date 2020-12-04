#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Imports the Tsuut'ina dictionary content into the DB.

-----------------------------------
How to import the OneSpot-Sapir CSV
-----------------------------------

Paraphrased from Dr. Chris Cox:

* If an entry starts with a star, it's an ungrammatical form; leave it out
* <ɫ> U+026B, LATIN SMALL LETTER L WITH MIDDLE TILDE should be normalized to
  <ł> U+0142, LATIN SMALL LETTER L WITH STROKE
* Corollary: orthography normalization should treat the two characters above
  equivalently!
* "Not for school edition" are words that... may be NSFW. So tag them as such?
* The "Folio" column cites where the word came from in the books.

"""

import csv
import io
import logging
import re
from collections import defaultdict
from hashlib import sha1, sha384
from pathlib import Path
from typing import Dict, List, Set, Tuple

from django.conf import settings
from django.db import transaction
from django.db.utils import OperationalError

from apps.gunaha.models import OnespotDuplicate
from apps.morphodict.models import Definition, DictionarySource, Head

from .orthography import nfc, normalize_orthography

# We populate the “through” model linking Definitions to their sources directly,
# because that is WAY more efficient than adding a source to each Definition manually.
Definition2Source = Definition.citations.through

logger = logging.getLogger(__name__)

private_dir = settings.DATA_DIR / "private"


class DictionaryImportError(RuntimeError):
    """
    When something goes wrong during the dictionary import process.
    """


def import_dictionary(purge: bool = False) -> None:
    logger.info("Importing OneSpot-Sapir vocabulary list")

    filename = "Onespot-Sapir-Vocabulary-list-OS-Vocabulary.tsv"
    path_to_tsv = private_dir / filename
    if not path_to_tsv.exists():
        raise DictionaryImportError(f"Cannot find dictionary file: {path_to_tsv}")

    with open(path_to_tsv, "rb") as raw_file:
        raw_bytes = raw_file.read()

    file_hash = sha384(raw_bytes).hexdigest()
    assert len(file_hash) == 384 // 4
    tsv_file = io.StringIO(raw_bytes.decode("UTF-8"))

    logger.info("Importing %s [SHA-384: %s]", path_to_tsv, file_hash)

    # Purge only once we KNOW we have dictionary content

    if purge:
        with transaction.atomic():
            logger.warn("Purging ALL existing dictionary content")
            Definition2Source.objects.all().delete()
            Definition.objects.all().delete()
            Head.objects.all().delete()
            DictionarySource.objects.all().delete()

    if not should_import_onespot(file_hash):
        logger.info("Already imported %s; skipping...", path_to_tsv)
        return

    onespot = DictionarySource(
        abbrv="Onespot",
        title="Onespot-Sapir vocabulary list",
        editor="Bruce Starlight, John Onespot, Edward Sapir",
        import_filename=filename,
        last_import_sha384=file_hash,
    )

    heads: Dict[str, Head] = {}
    # In case the same head maps to an existing entry ID
    text_wc_to_id: Dict[Tuple[str, str], str] = {}
    duplicates: List[OnespotDuplicate] = []
    definitions: Dict[int, Definition] = {}
    mappings: Set[Tuple[int, int]] = set()

    entries = csv.DictReader(tsv_file, delimiter="\t")
    for entry in entries:
        term = normalize_orthography(entry["Bruce - Tsuut'ina text"])

        if should_skip_importing_head(term, entry):
            continue

        ############################# Prepare head #####################################

        primary_key = entry["ID"]

        word_class = entry["Part of speech"]
        unique_tag = (term, word_class)

        if existing_entry := text_wc_to_id.get(unique_tag):
            duplicates.append(
                OnespotDuplicate(
                    entry_id=primary_key, duplicate_of=heads[existing_entry]
                )
            )
            logger.info(
                "%s (%r) is a duplicate of %s", primary_key, unique_tag, existing_entry
            )
            primary_key = existing_entry
        else:
            text_wc_to_id[unique_tag] = primary_key

        # setdefault() will only insert an entry the first time on duplicates.
        # the first entry in the spreadsheet usually has the most information
        head = heads.setdefault(
            primary_key, Head(pk=primary_key, text=term, word_class=word_class)
        )

        # TODO: tag certain words as "not suitable for school" -- I guess NSFW?
        # TODO: tag heads with "Folio" -- more specifically where the word came from

        ########################## Prepare definition ##################################

        definition = nfc(entry["Bruce - English text"])
        if not definition:
            continue

        pk = make_primary_key(definition, str(head.pk))
        dfn = Definition(pk=pk, text=definition, defines=head)
        if pk in definitions:
            old_definition = definitions[pk]
            if dfn.text != old_definition.text:
                logger.error(f"hash collision: {dfn} / {old_definition}")
                continue
            else:
                logger.info("Duplicate definition: {dfn}")
        else:
            definitions[pk] = dfn

        mappings.add((pk, onespot.pk))

    logger.info(
        "Will insert: heads: %d, defs: %d", len(heads), len(definitions),
    )

    with transaction.atomic():
        DictionarySource.objects.bulk_create([onespot])
        Head.objects.bulk_create(heads.values())
        Definition.objects.bulk_create(definitions.values())
        Definition2Source.objects.bulk_create(
            Definition2Source(definition_id=def_pk, dictionarysource_id=dict_pk)
            for def_pk, dict_pk in mappings
        )
        OnespotDuplicate.objects.bulk_create(duplicates)

    logger.info("Done importing from %s", path_to_tsv)


def should_skip_importing_head(head: str, info: dict) -> bool:
    if head == "":
        logger.warn("Skipping entry without dictionary head: %r", info)
        return True

    if head.startswith("*") or head.endswith("*"):
        logger.debug("Skipping ungrammatical form: %r", head)
        return True

    if "??" in head:
        logger.debug(
            "Skipping head labelled with '???' (see Folio %s)",
            info.get("Folio", "<unknown>"),
        )
        return True

    return False


def make_primary_key(*args: str) -> int:
    """
    Creates a hash of the arguments.
    """
    number = int(sha1("\n".join(args).encode("UTF-8")).hexdigest(), base=16)
    return number & 0xFFFFFFFF


def should_import_onespot(file_hash: str) -> bool:
    try:
        ds = DictionarySource.objects.get(abbrv="Onespot")
    except OperationalError:
        logger.error("Database does not yet exist...")
        return False
    except DictionarySource.DoesNotExist:
        logger.info("Importing for the first time!")
        return True

    if ds.last_import_sha384 == file_hash:
        return False
    return True
