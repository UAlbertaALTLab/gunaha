from django.db import models

from .search import HeadSearchMixin

MAX_HEAD_LENGTH = 64
MAX_ENTRY_ID_LENGTH = 8
MAX_DEFINITION_LENGTH = 256
BITS_PER_HEX_CHAR = 4


class HeadManager(models.Manager, HeadSearchMixin):
    """
    Customizes search for Head models. Adds the following convenience method:


        Head.objects.search(query) -> SearchQuerySet
    """

    # See ./search.py for implementation!


class Head(models.Model):
    """
    A linguistic utterance that can be defined.

        - a phrase
        - a morpheme
        - a wordform
            - a wordform that is a lemma
    """

    entry_id = models.CharField(
        primary_key=True,
        max_length=MAX_ENTRY_ID_LENGTH,
        help_text="Unique ID for this head.",
    )

    text = models.CharField(max_length=MAX_HEAD_LENGTH)
    word_class = models.CharField(max_length=16)

    # Enables you to do this:
    #
    #   Head.objects.search("dog") -> search results for "dog"
    objects = HeadManager()

    class Meta:
        unique_together = ("text", "word_class")
        # Orders alphabetically. Note that this may not make sense in the given language
        # (collating is hard)
        ordering = ["text"]

    def __str__(self) -> str:
        return f"{self.text} ({self.word_class})"


class DictionarySource(models.Model):
    """
    Represents bibliographic information for a set of definitions.

    A Definition is said to cite a DictionarySource.
    """

    # A short, unique, uppercased ID. This will be exposed to users!
    #  e.g., CW for "Cree: Words"
    #     or MD for "Maskwacîs Dictionary"
    abbrv = models.CharField(
        max_length=12,
        primary_key=True,
        help_text="A short identifier for the dicionary source",
    )

    title = models.CharField(
        max_length=256,
        null=False,
        blank=False,
        help_text="What is the primary title of the dictionary source?",
    )
    editor = models.CharField(
        max_length=512,
        blank=True,
        help_text=(
            "Who edited or compiled this volume? "
            "Separate multiple editors with commas."
        ),
    )

    import_filename = models.CharField(
        max_length=128,
        help_text="The file that imported these entries",
        editable=False,
        null=False,
        blank=False,
    )
    last_import_sha384 = models.CharField(
        max_length=384 // BITS_PER_HEX_CHAR,
        help_text="SHA-384 hash (hexadecimal) of the imported file",
        null=False,
        blank=False,
        editable=False,
    )

    def __str__(self):
        """
        Will print a short citation like:

            [CW] “Cree : Words” (Ed. Arok Wolvengrey)
        """
        # These should ALWAYS be present
        abbrv = self.abbrv
        title = self.title

        author_or_editor = f"(Ed. {self.editor})"

        return f"[{abbrv}]: “{title}” {author_or_editor}"


class Definition(models.Model):
    """
    One of several possible meanings for the head.
    """

    text = models.CharField(max_length=MAX_DEFINITION_LENGTH)
    defines = models.ForeignKey(
        Head, on_delete=models.CASCADE, related_name="definitions"
    )

    # A definition **cites** one or more dictionary sources.
    citations = models.ManyToManyField(DictionarySource)

    def __str__(self) -> str:
        return f"{self.text}"
