"""
constants
"""
from enum import Enum

# type alias
from typing import NamedTuple, NewType

# types
# analysis but concatenated
ConcatAnalysis = NewType("ConcatAnalysis", str)
FSTLemma = NewType("FSTLemma", str)

FSTTag = NewType("FSTTag", str)
Label = NewType("Label", str)


ISOLanguage = NewType("ISOLanguage", str)


class ParadigmSize(Enum):
    BASIC = "BASIC"
    FULL = "FULL"
    LINGUISTIC = "LINGUISTIC"

    @property
    def display_form(self):
        """
        the form that we show to users on paradigm table
        """
        return self.value.capitalize()


class Analysis(NamedTuple):
    """
    Analysis of a wordform.
    """

    raw_prefixes: str
    lemma: str
    raw_suffixes: str

    def concatenate(self) -> ConcatAnalysis:
        result = ""
        if self.raw_prefixes != "":
            result += self.raw_prefixes + "+"
        result += f"{self.lemma}+{self.raw_suffixes}"
        return ConcatAnalysis(result)
