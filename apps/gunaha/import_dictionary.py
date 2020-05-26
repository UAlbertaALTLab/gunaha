#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import csv
import logging
from hashlib import sha384
from pathlib import Path

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

    logger.info("Importing %s [SHA-384: %s]", path_to_tsv, file_hash)
