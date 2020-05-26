import logging
import unicodedata
from functools import cmp_to_key, partial
from itertools import chain
from typing import Any, Callable, NamedTuple, NewType, Optional, Set, Tuple, Union, cast

import attr
from attr import attrs
from django.conf import settings
from django.db import models, transaction
from django.db.models import Max, Q, QuerySet
from django.forms import model_to_dict
from django.urls import reverse
from django.utils.encoding import iri_to_uri
from django.utils.functional import cached_property
from sortedcontainers import SortedSet

from .affix_search import AffixSearcher
from .constants import ConcatAnalysis, ISOLanguage
from .schema import SerializedDefinition, SerializedSearchResult, SerializedWordform

logger = logging.getLogger(__name__)


@attrs(auto_attribs=True, frozen=True)  # frozen makes it hashable
class SearchResult:
    """
    Contains all of the information needed to display a search result.

    Comment:
    Each instance corresponds visually to one card shown on the interface
    """

    # the text of the match
    matched_text: str
    # What language the text of the match is
    matched_by: ISOLanguage

    # Did we match a dictionary head?
    is_head: bool

    # The matched lemma
    lemma_wordform: "Wordform"

    # triple dots in type annotation means they can be empty

    # user friendly linguistic breakdowns
    linguistic_breakdown_head: Tuple[str, ...]
    linguistic_breakdown_tail: Tuple[str, ...]

    definitions: Tuple["Definition", ...]

    def serialize(self) -> SerializedSearchResult:
        """
        serialize the instance, can be used before passing into a template / in an API view, etc.
        """
        # note: passing in serialized "dumb" object instead of smart ones to templates is a Django best practice
        # it avoids unnecessary database access and makes APIs easier to create
        result = attr.asdict(self)
        # lemma field will refer to lemma_wordform itself, which makes it impossible to serialize
        result["lemma_wordform"] = self.lemma_wordform.serialize()

        result["matched_by"] = self.matched_by
        result["definitions"] = [
            definition.serialize() for definition in self.definitions
        ]
        return cast(SerializedSearchResult, result)


NormatizedCree = NewType("NormatizedCree", str)
MatchedEnglish = NewType("MatchedEnglish", str)


class Wordform(models.Model):
    # initialized in apps.py
    affix_searcher: AffixSearcher

    def get_absolute_url(self) -> str:
        """
        :return: url that looks like
         "/words/nipaw" "/words/nipâw?pos=xx" "/words/nipâw?full_lc=xx" "/words/nipâw?analysis=xx" "/words/nipâw?id=xx"
         it's the least strict url that guarantees unique match in the database
        """
        assert self.is_lemma, "There is no page for non-lemmas"
        lemma_url = reverse(
            "cree-dictionary-index-with-lemma", kwargs={"lemma_text": self.text}
        )
        if self.homograph_disambiguator is not None:
            lemma_url += f"?{self.homograph_disambiguator}={getattr(self, self.homograph_disambiguator)}"

        return iri_to_uri(lemma_url)

    def serialize(self) -> SerializedWordform:
        """

        :return: json parsable result
        """
        result = model_to_dict(self)
        result["definitions"] = [
            definition.serialize() for definition in self.definitions.all()
        ]
        result["lemma_url"] = self.get_absolute_url()
        return result

    @cached_property
    def homograph_disambiguator(self) -> Optional[str]:
        """
        :return: the least strict field name that guarantees unique match together with the text field.
            could be pos, full_lc, analysis, id or None when the text is enough to disambiguate
        """
        homographs = Wordform.objects.filter(text=self.text)
        if homographs.count() == 1:
            return None
        for field in "pos", "full_lc", "analysis":
            if homographs.filter(**{field: getattr(self, field)}).count() == 1:
                return field
        return "id"  # id always guarantees unique match

    # override pk to allow use of bulk_create
    # auto-increment is also implemented in the overridden save() method below
    id = models.PositiveIntegerField(primary_key=True)

    # The actual size of the word form.
    text = models.CharField(max_length=128)

    lexical_category = models.CharField(
        max_length=10,
        help_text="Full lexical category directly from source",  # e.g. NI-3
    )

    pos = models.CharField(
        max_length=12,
        help_text="Part of speech parsed from source. Can be unspecified",
    )

    analysis = models.CharField(
        max_length=50,
        default="",
        help_text="fst analysis or the best possible generated if the source is not analyzable",
        # see xml_importer.py::generate_as_is_analysis
    )
    is_lemma = models.BooleanField(
        default=False,
        help_text="The wordform is chosen as lemma. This field defaults to true if according to fst the wordform is not"
        " analyzable or it's ambiguous",
    )

    # if as_is is False. pos field is guaranteed to be not empty
    # and will be values from `constants.POS` enum class

    # if as_is is True, full_lc and pos fields can be under-specified, i.e. they can be empty strings
    as_is = models.BooleanField(
        default=False,
        help_text="The lemma of this wordform is not determined during the importing process."
        "is_lemma defaults to true and lemma field defaults to self",
    )

    lemma = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="inflections",
        help_text="The identified lemma of this wordform. Defaults to self",
    )

    class Meta:
        # analysis is for faster user query (in function fetch_lemma_by_user_query below)
        # text is for faster fuzzy search initialization when the app restarts on the server side (order_by text)
        # text index also benefits fast lemma matching in function fetch_lemma_by_user_query
        indexes = [
            models.Index(fields=["analysis"]),
            models.Index(fields=["text"]),
        ]

    def __str__(self):
        return self.text

    def __repr__(self):
        cls_name = type(self).__name__
        return f"<{cls_name}: {self.text} {self.analysis}>"

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Ensure id is auto-incrementing.
        Infer foreign key 'lemma' to be self if self.is_lemma is set to True. (friendly to test creation)
        """
        max_id = Wordform.objects.aggregate(Max("id"))
        if max_id["id__max"] is None:
            self.id = 0
        else:
            self.id = max_id["id__max"] + 1

        # infer lemma if it is not set.
        # this helps with adding entries in django admin as the ui for
        # `lemma` takes forever to load.
        # Also helps with tests as it's now easier to create entries

        if self.is_lemma:
            self.lemma_id = self.id

        super(Wordform, self).save(*args, **kwargs)

    @staticmethod
    def fetch_lemma_by_user_query(user_query: str, **kwargs) -> "CreeAndEnglish":
        """
        treat the user query as cree and:

        Give the analysis of user query and matched lemmas.
        There can be multiple analysis for user queries
        One analysis could match multiple lemmas as well due to underspecified database fields.
        (lc and pos can be empty)

        treat the user query as English keyword and:

        Give a list of matched lemmas

        :param user_query: can be English or Cree (syllabics or not)
        :param kwargs: additional fields to disambiguate
        """
        # Whitespace won't affect results, but the FST can't deal with it:
        user_query = user_query.strip()
        # Normalize to UTF8 NFC
        user_query = unicodedata.normalize("NFC", user_query)
        user_query = (
            user_query.replace("ā", "â")
            .replace("ē", "ê")
            .replace("ī", "î")
            .replace("ō", "ô")
        )

        user_query = user_query.lower()

        # build up result_lemmas in 2 ways
        # 1. affix search (return all results that ends/starts with the query string)
        # 2. spell relax in descriptive fst
        # 2. definition containment of the query word

        cree_results: Set[CreeResult] = set()

        # there will be too many matches for some shorter queries
        if len(user_query) > settings.AFFIX_SEARCH_THRESHOLD:
            # prefix and suffix search
            ids_by_prefix = Wordform.affix_searcher.search_by_prefix(user_query)
            ids_by_suffix = Wordform.affix_searcher.search_by_suffix(user_query)

            for wf in Wordform.objects.filter(
                id__in=set(chain(ids_by_prefix, ids_by_suffix))
            ):
                cree_results.add(CreeResult(wf.analysis, wf, wf.lemma))

        # TODO: there is no FST, so there are no analyses ¯\_(ツ)_/¯
        fst_analyses: Set[ConcatAnalysis] = set()

        for analysis in fst_analyses:
            # todo: test

            exactly_matched_wordforms = Wordform.objects.filter(
                analysis=analysis, as_is=False, **kwargs
            )

            if exactly_matched_wordforms.exists():
                for wf in exactly_matched_wordforms:
                    cree_results.add(
                        CreeResult(ConcatAnalysis(wf.analysis), wf, Lemma(wf.lemma))
                    )
            else:
                # When the user query is outside of paradigm tables
                # e.g. mad preverb and reduplication: ê-mâh-misi-nâh-nôcihikocik
                # e.g. Initial change: nêpât: {'IC+nipâw+V+AI+Cnj+Prs+3Sg'}
                # e.g. Err/Orth: ewapamat: {'PV/e+wâpamêw+V+TA+Cnj+Prs+3Sg+4Sg/PlO+Err/Orth'

                logger.error(
                    f"fst_analysis_parser cannot understand analysis {analysis}"
                )
                continue

        # Words/phrases with spaces in CW dictionary can not be analyzed by fst and are labeled "as_is".
        # However we do want to show them. We trust CW dictionary here and filter those lemmas that has any definition
        # that comes from CW

        # now we get results searched by English
        # todo: remind user "are you searching in cree/english?"
        # todo: allow inflected forms to be searched through English. (requires database migration
        #  since now EnglishKeywords are bound to lemmas)
        english_results: Set[EnglishResult] = set()
        if " " not in user_query:  # a whole word

            # this requires database to be changed as currently EnglishKeyword are associated with lemmas
            lemma_ids = EnglishKeyword.objects.filter(
                text__iexact=user_query, **kwargs
            ).values("lemma__id")
            for wordform in Wordform.objects.filter(
                id__in=lemma_ids, as_is=False, **kwargs
            ):
                english_results.add(
                    EnglishResult(MatchedEnglish(user_query), wordform, Lemma(wordform))
                )  # will become  (user_query, inflection.text, inflection.lemma)

            # explained above, preverbs should be presented
            for wordform in Wordform.objects.filter(
                Q(pos="IPV") | Q(full_lc="IPV") | Q(pos="PRON"),
                id__in=lemma_ids,
                as_is=True,
                **kwargs,
            ):
                english_results.add(
                    EnglishResult(MatchedEnglish(user_query), wordform, Lemma(wordform))
                )  # will become  (user_query, inflection.text, wordform)

        return CreeAndEnglish(cree_results, english_results)

    @staticmethod
    def search(user_query: str, **kwargs) -> SortedSet[SearchResult]:
        """

        :param user_query:
        :param kwargs: additional fields to disambiguate
        :return:
        """
        cree_results: Set[CreeResult]
        english_results: Set[EnglishResult]

        cree_results, english_results = Wordform.fetch_lemma_by_user_query(
            user_query, **kwargs
        )

        results: SortedSet[SearchResult] = SortedSet(key=sort_by_user_query(user_query))

        # Create the search results
        for cree_result in cree_results:
            matched_cree = cree_result.normatized_cree_text
            if isinstance(cree_result.normatized_cree, Wordform):
                is_lemma = cree_result.normatized_cree.is_lemma
                definitions = tuple(cree_result.normatized_cree.definitions.all())
            else:
                is_lemma = False
                definitions = ()

            # todo: tags
            results.add(
                SearchResult(
                    matched_text=matched_cree,
                    is_head=True,
                    # TODO: srs
                    matched_by=ISOLanguage("crk"),
                    linguistic_breakdown_head=(),
                    linguistic_breakdown_tail=(),
                    lemma_wordform=cree_result.lemma,
                    definitions=definitions,
                )
            )

        for result in english_results:
            results.add(
                SearchResult(
                    matched_text=result.matched_cree.text,
                    is_head=True,
                    matched_by=ISOLanguage("eng"),
                    lemma_wordform=result.matched_cree.lemma,
                    linguistic_breakdown_head=(),
                    linguistic_breakdown_tail=(),
                    definitions=tuple(result.matched_cree.definitions.all()),
                    # todo: current EnglishKeyword is bound to
                    #       lemmas, whose definitions are guaranteed in the database.
                    #       This may be an empty tuple in the future
                    #       when EnglishKeyword can be associated with non-lemmas
                )
            )

        return results


# it's a str when the preverb does not exist in the database
Preverb = Union[Wordform, str]


def sort_by_user_query(user_query: str) -> Callable[[Any], Any]:
    """
    Returns a key function that sorts search results ranked by their distance
    to the user query.
    """
    # mypy doesn't really know how to handle partial(), so we tell it the
    # correct type with cast()
    # See: https://github.com/python/mypy/issues/1484
    return cmp_to_key(
        cast(
            Callable[[Any, Any], Any],
            partial(sort_search_result, user_query=user_query),
        )
    )


Lemma = NewType("Lemma", Wordform)


class CreeResult(NamedTuple):
    """
    - analysis: a string, fst analysis of normatized cree

    - normatized_cree: a wordform, the Cree inflection that matches the analysis
        Can be a string that's not saved in the database since our database do not store all the
        weird inflections

    - lemma: a Wordform object, the lemma of the matched inflection
    """

    analysis: ConcatAnalysis
    normatized_cree: Union[Wordform, str]
    lemma: Lemma

    @property
    def normatized_cree_text(self) -> str:
        if isinstance(self.normatized_cree, Wordform):
            return self.normatized_cree.text
        else:  # is str
            return self.normatized_cree


class EnglishResult(NamedTuple):
    """
    - matched_english: a string, the English that matches user query, currently it will just be the same as user query.
        (unicode normalized, lowercased)

    - normatized_cree: a string, the Cree inflection that matches the English

    - lemma: a Wordform object, the lemma of the matched inflection
    """

    matched_english: MatchedEnglish
    matched_cree: Wordform
    lemma: Lemma


def sort_search_result(
    res_a: SearchResult, res_b: SearchResult, user_query: str
) -> float:
    """
    determine how we sort search results.

    :return:   0: does not matter;
              >0: res_a should appear after res_b;
              <0: res_a should appear before res_b.
    """
    # TODO: implement this!
    return 0


class CreeAndEnglish(NamedTuple):
    """
    Duct tapes together two kinds of search results:

     - cree results -- an ordered set of CreeResults, should be sorted by the modified levenshtein distance between the
        analysis and the matched normatized form
     - english results -- an ordered set of EnglishResults, sorting mechanism is to be determined
    """

    # MatchedCree are inflections
    cree_results: Set[CreeResult]
    english_results: Set[EnglishResult]


class DictionarySource(models.Model):
    """
    Represents bibliographic information for a set of definitions.

    A Definition is said to cite a DictionarySource.
    """

    # A short, unique, uppercased ID. This will be exposed to users!
    #  e.g., CW for "Cree: Words"
    #     or MD for "Maskwacîs Dictionary"
    abbrv = models.CharField(max_length=8, primary_key=True)

    # Bibliographic information:
    title = models.CharField(
        max_length=256,
        null=False,
        blank=False,
        help_text="What is the primary title of the dictionary source?",
    )
    author = models.CharField(
        max_length=512,
        blank=True,
        help_text="Separate multiple authors with commas. See also: editor",
    )
    editor = models.CharField(
        max_length=512,
        blank=True,
        help_text=(
            "Who edited or compiled this volume? "
            "Separate multiple editors with commas."
        ),
    )
    year = models.IntegerField(
        null=True, blank=True, help_text="What year was this dictionary published?"
    )
    publisher = models.CharField(
        max_length=128, blank=True, help_text="What was the publisher?"
    )
    city = models.CharField(
        max_length=64, blank=True, help_text="What is the city of the publisher?"
    )

    def __str__(self):
        """
        Will print a short citation like:

            [CW] “Cree : Words” (Ed. Arok Wolvengrey)
        """
        # These should ALWAYS be present
        abbrv = self.abbrv
        title = self.title

        # Both of these are optional:
        author = self.author
        editor = self.editor

        author_or_editor = ""
        if author:
            author_or_editor += f" by {author}"
        if editor:
            author_or_editor += f" (Ed. {editor})"

        return f"[{abbrv}]: “{title}”{author_or_editor}"


class Definition(models.Model):
    # override pk to allow use of bulk_create
    id = models.PositiveIntegerField(primary_key=True)

    text = models.CharField(max_length=200)

    # A definition **cites** one or more dictionary sources.
    citations = models.ManyToManyField(DictionarySource)

    # A definition defines a particular wordform
    wordform = models.ForeignKey(
        Wordform, on_delete=models.CASCADE, related_name="definitions"
    )

    # Why this property exists:
    # because DictionarySource should be its own model, but most code only
    # cares about the source IDs. So this removes the coupling to how sources
    # are stored and returns the source IDs right away.
    @property
    def source_ids(self):
        """
        A tuple of the source IDs that this definition cites.
        """
        return tuple(sorted(source.abbrv for source in self.citations.all()))

    def serialize(self) -> SerializedDefinition:
        """
        :return: json parsable format
        """
        return {"text": self.text, "source_ids": self.source_ids}

    def __str__(self):
        return self.text


class EnglishKeyword(models.Model):
    # override pk to allow use of bulk_create
    id = models.PositiveIntegerField(primary_key=True)

    text = models.CharField(max_length=20)

    lemma = models.ForeignKey(
        Wordform, on_delete=models.CASCADE, related_name="english_keyword"
    )

    class Meta:
        indexes = [models.Index(fields=["text"])]
