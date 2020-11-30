#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Imports Bruce's recordings. Assumes the following database:

    CREATE TABLE entry (
        id              TEXT PRIMARY KEY NOT NULL,
        transcription   TEXT NOT NULL
    );
    CREATE TABLE recording (
        hash        TEXT NOT NULL,
        entry_id    TEXT NOT NULL,
        audio       BLOB NOT NULL,

        FOREIGN KEY (entry_id) REFERENCES entry(id)
    );

The recording itself is a raw .wav file that must be transcoded to .m4a before being
accessible to the website.

Then entry_id are Onespot IDs. Note that they may refer to duplicates, so check if
they're in OnespotDuplicate first before associating it with a Head.
"""

import io
import logging
import sqlite3
import tempfile
from typing import Optional

from django.core.files import File
from pydub import AudioSegment  # type: ignore

from apps.gunaha.models import OnespotDuplicate, Recording
from apps.morphodict.models import Head

logger = logging.getLogger(__name__)


def import_recordings(database_path: str):
    conn = sqlite3.connect(database_path)

    # Figure out which entry each recording should attach to.
    cursor = conn.execute("SELECT entry_id FROM recording")
    onespot_ids = {osid for osid, in cursor.fetchall()}

    id_to_head = {}
    for entry_id in onespot_ids:
        if duplicate := get_duplicate(entry_id):
            head = duplicate
        else:
            try:
                head = Head.objects.get(pk=entry_id)
            except Head.DoesNotExist:
                logger.error("could not find head for %r", entry_id)
                continue
        id_to_head[entry_id] = head

    # cool, let's transcode audio!
    with tempfile.TemporaryDirectory() as work_directory:
        cursor = conn.execute("SELECT hash, entry_id, audio FROM recording")
        for file_hash, entry_id, raw_wav_data in cursor:
            if entry_id not in id_to_head:
                continue

            head = id_to_head[entry_id]
            with io.BytesIO(raw_wav_data) as source_data:
                segment = AudioSegment.from_wav(source_data)
            # TODO: add metadata, because why not?
            audio_file = segment.export(
                f"{work_directory}/audio.m4a", format="ipod", codec="aac"
            )
            recording = Recording(
                entry=head, compressed_audio=File(audio_file, name=f"{file_hash}.m4a"),
            )
            recording.save()
            audio_file.close()


def get_duplicate(entry_id: str) -> Optional[Head]:
    try:
        duplicate = OnespotDuplicate.objects.get(pk=entry_id)
    except OnespotDuplicate.DoesNotExist:
        return None
    else:
        return duplicate.duplicate_of
