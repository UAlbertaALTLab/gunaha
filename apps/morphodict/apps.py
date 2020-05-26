import logging
import string
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from django.apps import AppConfig
from django.conf import settings
from django.db import OperationalError, connection

from .affix_search import AffixSearcher
from .utils import shared_res_dir

logger = logging.getLogger(__name__)


class MorphoDictConfig(AppConfig):
    # TODO: This should not be in "apps.morphodict..."
    name = "apps.morphodict"
    verbose_name = "Morphological Dictionary"

    def ready(self):
        """
        This function is called prior to app start.
        It initializes fuzzy search (build the data structure).
        It also hashes preverbs for faster preverb matching.
        """
        initialize_affix_search()


def initialize_affix_search():
    """
    build tries and attach to Wordform class to facilitate prefix/suffix search
    """
    logger.info("Building tries for affix search...")
    from .models import Wordform

    # TODO: use Tsuut'ina orthography instead.
    cree_letter_to_ascii = {
        ascii_letter: ascii_letter for ascii_letter in string.ascii_lowercase
    }
    cree_letter_to_ascii.update(
        {"â": "a", "ā": "a", "ê": "e", "ē": "e", "ī": "i", "î": "i", "ô": "o", "ō": "o"}
    )
    try:
        lowered_no_diacritics_text_with_id = [
            ("".join([cree_letter_to_ascii.get(c, c) for c in text.lower()]), wf_id)
            for text, wf_id in Wordform.objects.filter(is_lemma=True).values_list(
                "text", "id"
            )
        ]
        # apps.py will also get called during migration, it's possible that neither Wordform table nor text field
        # exists. Then an OperationalError will occur.
    except OperationalError:
        return

    Wordform.affix_searcher = AffixSearcher(lowered_no_diacritics_text_with_id)
    logger.info("Finished building tries")
