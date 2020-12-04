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
from typing import Dict, List, Optional, Set, Tuple

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

ONESPOT_ID_PATTERN = re.compile(r"^(os\d{5})(\w)?$")


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

    importer = OnespotWordlistImporter(path_to_tsv)

    # Purge only once we KNOW we can read the dictionary.
    if purge:
        purge_all_existing_entries()

    importer.run()


class OnespotWordlistImporter:
    dictionary_source_id = "Onespot"

    def __init__(self, path_to_tsv: Path) -> None:
        self.path_to_tsv = path_to_tsv
        self.raw_bytes = path_to_tsv.read_bytes()
        self.file_hash = compute_hash_of_source(self.raw_bytes)
        self.dictionary_source = self.create_source_for_onespot_wordlist()

        # Data structures required during import:
        self.heads: Dict[str, Head] = {}
        # In case the same head maps to an existing entry ID
        self.text_wc_to_id: Dict[Tuple[str, str], str] = {}
        self.duplicates: List[OnespotDuplicate] = []
        self.definitions: Dict[int, Definition] = {}

    @property
    def filename(self) -> str:
        return self.path_to_tsv.name

    def run(self) -> None:
        if self.has_already_imported_tsv():
            return

        logger.info("Importing %s [SHA-384: %s]", self.path_to_tsv, self.file_hash)

        self.prepare_models_before_import()
        self.bulk_import()

        logger.info("Done importing from %s", self.path_to_tsv)

    def prepare_models_before_import(self) -> None:
        tsv_file = io.StringIO(self.raw_bytes.decode("UTF-8"))
        entries = csv.DictReader(tsv_file, delimiter="\t")
        for entry in entries:
            head = self.prepare_head_from_entry(entry)
            if head is None:
                # For whatever reason, we need to skip this entry:
                continue
            # TODO: this entry might define the PREVIOUS entry?
            self.prepare_definition_from_entry(entry, head)

    def prepare_head_from_entry(self, entry: Dict[str, str]) -> Optional[Head]:
        term = normalize_orthography(entry["Bruce - Tsuut'ina text"])

        # TODO: tag certain words as "not suitable for school" -- I guess NSFW?
        # TODO: tag heads with "Folio" -- more specifically where the word came from
        if should_skip_importing_head(term, entry):
            return None

        entry_id = entry["ID"]
        match = ONESPOT_ID_PATTERN.match(entry_id)
        if match is None:
            logger.warn("ID %s did not match expected ID pattern; skipped.", entry_id)
            return None

        primary_key, suffix = match.groups()
        if suffix:
            logger.warn(
                "discarding “%s” suffix from %s and hoping it all goes okay...",
                suffix,
                entry_id,
            )

        word_class = entry["Part of speech"]
        unique_tag = (term, word_class)

        if existing_entry := self.text_wc_to_id.get(unique_tag):
            self.duplicates.append(
                OnespotDuplicate(
                    entry_id=primary_key, duplicate_of=self.heads[existing_entry]
                )
            )
            logger.info(
                "%s (%r) is a duplicate of %s", primary_key, unique_tag, existing_entry,
            )
            primary_key = existing_entry
        else:
            self.text_wc_to_id[unique_tag] = primary_key

        # setdefault() will only insert an entry the first time on duplicates.
        # the first entry in the spreadsheet usually has the most information
        return self.heads.setdefault(
            primary_key, Head(pk=primary_key, text=term, word_class=word_class)
        )

    def prepare_definition_from_entry(self, entry: Dict[str, str], head: Head) -> None:
        definition = nfc(entry["Bruce - English text"])

        if not definition:
            # This entry does not provide a definition. Shoganai.
            return

        pk = make_primary_key(definition, str(head.pk))
        dfn = Definition(pk=pk, text=definition, defines=head)

        if old_definition := self.definitions.get(pk):
            if dfn.text != old_definition.text:
                raise DictionaryImportError(f"hash collision: {dfn} / {old_definition}")
            else:
                logger.info(f"Duplicate definition: “{dfn}”")
        else:
            self.definitions[pk] = dfn

    def bulk_import(self) -> None:
        logger.info(
            "Will insert: heads: %d, defs: %d", len(self.heads), len(self.definitions),
        )

        with transaction.atomic():
            DictionarySource.objects.bulk_create([self.dictionary_source])
            Head.objects.bulk_create(self.heads.values())
            Definition.objects.bulk_create(self.definitions.values())
            Definition2Source.objects.bulk_create(
                Definition2Source(
                    definition_id=definition_pk,
                    dictionarysource_id=self.dictionary_source_id,
                )
                for definition_pk in self.definitions.keys()
            )
            OnespotDuplicate.objects.bulk_create(self.duplicates)

    def create_source_for_onespot_wordlist(self) -> DictionarySource:
        return DictionarySource(
            abbrv=self.dictionary_source_id,
            title="Onespot-Sapir vocabulary list",
            editor="Bruce Starlight, John Onespot, Edward Sapir",
            import_filename=self.filename,
            last_import_sha384=self.file_hash,
        )

    def has_already_imported_tsv(self) -> bool:
        try:
            ds = DictionarySource.objects.get(abbrv=self.dictionary_source_id)
        except OperationalError:
            raise DictionaryImportError(
                "Database does not exist; please run migrations!"
            )
        except DictionarySource.DoesNotExist:
            logger.info("Importing %s for the first time!", self.path_to_tsv)
            return False

        if self.file_hash == ds.last_import_sha384:
            logger.info(
                "Already imported %s [SHA-384: %s]...",
                self.path_to_tsv,
                self.file_hash,
            )
            return True

        logger.info(
            "Different version of %s [old: %s; new: %s]",
            self.path_to_tsv,
            ds.last_import_sha384,
            self.file_hash,
        )
        return False


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


def compute_hash_of_source(raw_bytes: bytes) -> str:
    file_hash = sha384(raw_bytes).hexdigest()
    assert len(file_hash) == 384 // 4
    return file_hash


def purge_all_existing_entries() -> None:
    with transaction.atomic():
        logger.warn("Purging ALL existing dictionary content")
        Definition2Source.objects.all().delete()
        Definition.objects.all().delete()
        Head.objects.all().delete()
        DictionarySource.objects.all().delete()
