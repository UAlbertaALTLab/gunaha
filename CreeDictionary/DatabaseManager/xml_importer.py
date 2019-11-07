import datetime
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, List, Optional, Set, Tuple, NamedTuple

from colorama import Fore, init
from django.db import connection

from API.models import Definition, DictionarySource, EnglishKeyword, Inflection
from DatabaseManager import xml_entry_lemma_finder
from DatabaseManager.cree_inflection_generator import expand_inflections
from DatabaseManager.log import DatabaseManagerLogger
from constants import POS
from utils import fst_analysis_parser
from utils.crkeng_xml_utils import convert_lc_str, extract_l_str

init()  # for windows compatibility


logger = DatabaseManagerLogger(__name__)

RECOGNIZABLE_POS: Set[str] = {p[0] for p in Inflection.RECOGNIZABLE_POS}


def clear_database(verbose=True):
    """
    Delete data from database but keep admin authentication data
    """
    logger.set_print_info_on_console(verbose)
    logger.info("Deleting objects from the database")

    cursor = connection.cursor()

    # Raw SQL delete is a magnitude faster than Definition.objects.all.delete()
    cursor.execute("PRAGMA foreign_keys = OFF")

    # Delete Many-to-Many field first:
    cursor.execute("DELETE FROM API_definition_citations")

    # Then delete the rest:
    cursor.execute("DELETE FROM API_definition")
    cursor.execute("DELETE FROM API_inflection")
    cursor.execute("DELETE FROM API_englishkeyword")
    # do not delete dictionarysource, since it's editted on admin console and should persist
    # cursor.execute("DELETE FROM API_dictionarysource")
    cursor.execute("PRAGMA foreign_keys = ON")

    logger.info("All Objects deleted from Database")


def generate_as_is_analysis(xml_lemma: str, pos: str, lc: str) -> str:
    """
    generate analysis for xml entries whose fst analysis cannot be determined.
    The philosophy is to match the appearance an fst analysis
    in the following examples, the xml_lemmas are not necessarily un-analyzable. They are just examples to show the
    behaviour of this function.

    >>> generate_as_is_analysis('ihtatwêwitam', 'V', 'VTI') # adopt more detailed lc if possible
    'ihtatwêwitam+V+TI'
    >>> generate_as_is_analysis('wayawîwin', 'N', 'NI-2') # adopt more detailed lc if possible, strip dash-x to simulate fst analysis
    'wayawîwin+N+I'
    >>> generate_as_is_analysis('wayawîwin', '', 'NI') # adopt more detailed lc if possible, strip dash-x to simulate fst analysis
    'wayawîwin+N+I'
    >>> generate_as_is_analysis('wayawîwin', 'N', 'IPP') # ignore lc outside constants.LexicalCategory Enum
    'wayawîwin+N'
    >>> generate_as_is_analysis('wayawîwin', 'N', '') # use pos only as a fallback
    'wayawîwin+N'
    >>> generate_as_is_analysis('wayawîwin', '', '') # no analysis when there's no pos nor lc
    ''
    >>> generate_as_is_analysis('wayawîwin', '', 'IPP') # ignore lc outside constants.LexicalCategory Enum
    ''
    """

    # possible parsed pos str
    # {'', 'IPV', 'Pron', 'N', 'Ipc', 'V', '-'}

    # possible parsed lc str
    # {'', 'NDA-1', 'NDI-?', 'NA-3', 'NA-4w', 'NDA-2', 'VTI-2', 'NDI-3', 'NDI-x', 'NDA-x',
    # 'IPJ  Exclamation', 'NI-5', 'NDA-4', 'VII-n', 'NDI-4', 'VTA-2', 'IPH', 'IPC ;; IPJ',
    # 'VAI-v', 'VTA-1', 'NI-3', 'VAI-n', 'NDA-4w', 'IPJ', 'PrI', 'NA-2', 'IPN', 'PR', 'IPV',
    # 'NA-?', 'NI-1', 'VTA-3', 'NI-?', 'VTA-4', 'VTI-3', 'NI-2', 'NA-4', 'NDI-1', 'NA-1', 'IPP',
    # 'NI-4w', 'INM', 'VTA-5', 'PrA', 'NDI-2', 'IPC', 'VTI-1', 'NI-4', 'NDA-3', 'VII-v', 'Interr'}

    lc = lc.split("-")[0]

    recognized_lc = convert_lc_str(lc)

    if recognized_lc is None:
        if pos not in ("", "-"):
            return xml_lemma + "+" + pos
        else:
            return ""
    else:
        return xml_lemma + recognized_lc.to_fst_output_style()


def format_element_error(msg: str, element: ET.Element) -> str:
    """
    format a message about an element and prettified xml for the element

    e.g.

    missing <lc> element

    <e>
        <t>blah</t>
    </e>
    """
    return f"{msg} \n {ET.tostring(element, encoding='unicode')}"


class EngcrkCree(NamedTuple):
    """
    A cree word extracted from engcrk.xml.
    The corresponding wordform in the database is to be determined later
    """

    wordform: str
    pos: POS


def load_engcrk_xml(filename: Path) -> DefaultDict[EngcrkCree, List[str]]:
    """
    :return: Dict[EngcrkCree , [english1, english2, english3 ...]] pos is in uppercase
    """

    # The structure in engcrk.xml

    """
        <e>

            <lg xml:lang="eng">
                <l pos="N">August</l>
            </lg>

            <mg>
                <tg xml:lang="crk">
                    <trunc sources="MD">august. [The flying month].</trunc>
                    <t pos="N" rank="1.0">Ohpahow-pisim</t>
                </tg>
            </mg>

            <mg>
                <tg xml:lang="crk">
                    <trunc sources="CW">Flying-Up Moon; August</trunc>
                    <t pos="N" rank="1.0">ohpahowi-pîsim</t>
                </tg>
            </mg>
        </e>
    """

    filename = Path(filename)

    assert filename.exists(), "%s does not exist" % filename

    res: DefaultDict[EngcrkCree, List[str]] = defaultdict(list)

    root = ET.parse(str(filename)).getroot()
    elements = root.findall(".//e")

    for element in elements:
        l_element = element.find("lg/l")
        if l_element is None:
            logger.debug(
                format_element_error(f"<e> lacks an <l> in file {filename}", element)
            )
            continue

        if l_element.text is None:
            logger.debug(format_element_error("<l> does not have text", element))
            continue

        t_elements = element.findall("mg/tg/t")

        if not t_elements:
            logger.debug(
                format_element_error(f"<e> lacks <t> in file {filename}", element)
            )
            continue

        for t_element in t_elements:
            if t_element.text is None:
                logger.debug(
                    format_element_error(
                        f"<t> does not have text in file {filename}", element
                    )
                )
                continue
            cree_word = t_element.text
            pos_str = t_element.get("pos")
            assert pos_str is not None
            try:
                pos = POS(pos_str.upper())
            except ValueError:
                logger.debug(
                    format_element_error(
                        f"Cree word {cree_word} has a unrecognizable pos {pos_str}",
                        element,
                    )
                )
                continue

            res[EngcrkCree(cree_word, pos)].append(l_element.text)

    return res


def import_xmls(dir_name: Path, multi_processing: int = 1, verbose=True):
    """
    CLEARS the database (except admin authentication data) and import from an xml file

    :keyword verbose: print to stdout or not
    """
    crkeng_filename = dir_name / "crkeng.xml"
    engcrk_filename = dir_name / "engcrk.xml"

    assert crkeng_filename.exists() and engcrk_filename.exists()
    start_time = time.time()
    logger.set_print_info_on_console(verbose)
    clear_database()
    logger.info("Database cleared")

    root = ET.parse(str(crkeng_filename)).getroot()

    source_ids = [s.get("id") for s in root.findall(".//source")]

    logger.info("Sources parsed: %r", source_ids)
    for source_id in source_ids:
        src = DictionarySource(abbrv=source_id)
        src.save()
        logger.info("Created source: %s", source_id)

    logger.info("Loading English keywords...")
    engcrk_cree_to_keywords = load_engcrk_xml(engcrk_filename)
    logger.info("English keywords loaded")

    # value is definition string as key and its source as value
    xml_lemma_pos_lc_to_str_definitions = (
        {}
    )  # type: Dict[Tuple[str,str,str], Dict[str, Set[str]]]

    # One lemma could have multiple entries with different pos and lc
    xml_lemma_to_pos_lc = {}  # type: Dict[str, List[Tuple[str,str]]]

    elements = root.findall(".//e")
    logger.info("%d dictionary entries found" % len(elements))

    duplicate_xml_lemma_pos_lc_count = 0
    logger.info("extracting (xml_lemma, pos, lc) tuples")
    tuple_count = 0
    for element in elements:

        str_definitions_for_entry = {}  # type: Dict[str, Set[str]]
        for t in element.findall(".//mg//tg//t"):
            sources = t.get("sources")
            assert (
                sources is not None
            ), f"<t> does not have a source attribute in entry \n {ET.tostring(element, encoding='unicode')}"
            assert (
                t.text is not None
            ), f"<t> has empty content in entry \n {ET.tostring(element, encoding='unicode')}"
            if (
                t.text in str_definitions_for_entry
            ):  # duplicate definition within one <e>, not likely to happen
                str_definitions_for_entry[t.text] |= set(sources.split(" "))
            else:
                str_definitions_for_entry[t.text] = set(sources.split(" "))
        l_element = element.find("lg/l")
        assert (
            l_element is not None
        ), f"Missing <l> element in entry \n {ET.tostring(element, encoding='unicode')}"
        lc_element = element.find("lg/lc")
        assert (
            lc_element is not None
        ), f"Missing <lc> element in entry \n {ET.tostring(element, encoding='unicode')}"
        lc_str = lc_element.text

        if lc_str is None:
            lc_str = ""
        xml_lemma = extract_l_str(element)
        pos_attr = l_element.get("pos")
        assert (
            pos_attr is not None
        ), f"<l> lacks pos attribute in entry \n {ET.tostring(element, encoding='unicode')}"
        pos_str = pos_attr

        duplicate_lemma_pos_lc = False

        if xml_lemma in xml_lemma_to_pos_lc:

            if (pos_str, lc_str) in xml_lemma_to_pos_lc[xml_lemma]:
                duplicate_xml_lemma_pos_lc_count += 1
                duplicate_lemma_pos_lc = True
            else:
                tuple_count += 1
                xml_lemma_to_pos_lc[xml_lemma].append((pos_str, lc_str))
        else:
            tuple_count += 1
            xml_lemma_to_pos_lc[xml_lemma] = [(pos_str, lc_str)]

        if duplicate_lemma_pos_lc:
            logger.debug(
                f"xml_lemma: {xml_lemma} pos: {pos_str} lc: {lc_str} is a duplicate tuple"
            )

            tuple_definitions = xml_lemma_pos_lc_to_str_definitions[
                (xml_lemma, pos_str, lc_str)
            ]
            for str_definition, source_set in str_definitions_for_entry.items():
                if str_definition in tuple_definitions:
                    tuple_definitions[str_definition] |= source_set
                else:
                    tuple_definitions[str_definition] = source_set
        else:
            xml_lemma_pos_lc_to_str_definitions[
                (xml_lemma, pos_str, lc_str)
            ] = str_definitions_for_entry

    logger.info(
        f"{Fore.BLUE}%d entries have (lemma, pos, lc) duplicate to others. Their definition will be merged{Fore.RESET}"
        % duplicate_xml_lemma_pos_lc_count
    )
    logger.info("%d (xml_lemma, pos, lc) tuples extracted" % tuple_count)

    xml_lemma_pos_lc_to_analysis = xml_entry_lemma_finder.extract_fst_lemmas(
        xml_lemma_to_pos_lc, multi_processing
    )

    # these two will be imported to the database
    as_is_xml_lemma_pos_lc = []  # type: List[Tuple[str, str, str]]
    true_lemma_analyses_to_xml_lemma_pos_lc = (
        dict()
    )  # type: Dict[str, List[Tuple[str, str, str]]]

    dup_analysis_xml_lemma_pos_lc_count = 0

    for (xml_lemma, pos, lc), analysis in xml_lemma_pos_lc_to_analysis.items():
        if analysis != "":
            if analysis in true_lemma_analyses_to_xml_lemma_pos_lc:
                dup_analysis_xml_lemma_pos_lc_count += 1
                existing_tuple = true_lemma_analyses_to_xml_lemma_pos_lc[analysis][0]
                logger.debug(
                    f"xml_lemma: {xml_lemma} pos: {pos} lc: {lc} has duplicate fst lemma analysis to xml_lemma:"
                    f" {existing_tuple[0]} pos: {existing_tuple[1]} lc: {existing_tuple[2]}."
                    f" Their Definition will be merged."
                )

                # merge definition to first tuple
                target = xml_lemma_pos_lc_to_str_definitions[
                    true_lemma_analyses_to_xml_lemma_pos_lc[analysis][0]
                ]
                extra = xml_lemma_pos_lc_to_str_definitions[(xml_lemma, pos, lc)]

                for str_definition, source_set in extra.items():
                    if str_definition in target:
                        target[str_definition] |= source_set
                    else:
                        target[str_definition] = source_set

                true_lemma_analyses_to_xml_lemma_pos_lc[analysis].append(
                    (xml_lemma, pos, lc)
                )
            else:
                true_lemma_analyses_to_xml_lemma_pos_lc[analysis] = [
                    (xml_lemma, pos, lc)
                ]
        else:
            as_is_xml_lemma_pos_lc.append((xml_lemma, pos, lc))

    logger.info(
        f"{Fore.BLUE}%d (lemma, pos, lc) have duplicate fst lemma analysis to others.\nTheir definition will be merged{Fore.RESET}"
        % dup_analysis_xml_lemma_pos_lc_count
    )

    inflection_counter = 1
    definition_counter = 1
    keyword_counter = 1

    db_inflections: List[Inflection] = []
    db_definitions: List[Definition] = []
    db_keywords: List[EnglishKeyword] = []
    citations: Dict[int, Set[str]] = {}

    for xml_lemma, pos, lc in as_is_xml_lemma_pos_lc:
        recognizable_lc = convert_lc_str(lc)
        normalized_lc = ""
        normalized_pos = pos.upper()
        if recognizable_lc is not None:
            normalized_lc = recognizable_lc.value

        # is_lemma field defaults to true
        db_inflection = Inflection(
            id=inflection_counter,
            text=xml_lemma,
            analysis=generate_as_is_analysis(xml_lemma, pos, lc),
            pos=normalized_pos if normalized_pos in RECOGNIZABLE_POS else "",
            lc=normalized_lc,
            is_lemma=True,
            as_is=True,
        )

        # todo: create English Keywords for as-is lemmas
        # currently as_is words are not shown to users
        # so it's not necessary to add it here

        db_inflection.lemma = db_inflection
        db_inflection.default_spelling = db_inflection

        inflection_counter += 1
        db_inflections.append(db_inflection)

        str_definitions_source_strings = xml_lemma_pos_lc_to_str_definitions[
            (xml_lemma, pos, lc)
        ]

        for str_definition, source_strings in str_definitions_source_strings.items():
            db_definition = Definition(
                id=definition_counter, text=str_definition, lemma=db_inflection
            )

            # Figure out what citations we should be making.
            assert definition_counter not in citations
            citations[definition_counter] = set(source_strings)

            definition_counter += 1
            db_definitions.append(db_definition)

    expanded = expand_inflections(
        true_lemma_analyses_to_xml_lemma_pos_lc.keys(), multi_processing
    )

    logger.info("Structuring wordforms, english keywords, and definition objects...")
    for (
        true_lemma_analysis,
        xml_lemma_pos_lcs,
    ) in true_lemma_analyses_to_xml_lemma_pos_lc.items():

        db_lemmas = []
        db_inflections_for_analysis = []
        for generated_analysis, generated_inflections in expanded[true_lemma_analysis]:
            # db_lemmas could be of length more than one
            # for example peepeepoopoo+N+A+Sg may generate two spellings: pepepopo / peepeepoopoo

            if generated_analysis != true_lemma_analysis:
                is_lemma = False
            else:
                is_lemma = True

            generated_lc = fst_analysis_parser.extract_category(generated_analysis)
            assert generated_lc is not None
            generated_pos = generated_lc.pos

            default_spelling: Optional[Inflection] = None
            for i, generated_inflection in enumerate(generated_inflections):
                # generated_inflections contain different spellings of one fst analysis

                db_inflection = Inflection(
                    id=inflection_counter,
                    text=generated_inflection,
                    analysis=generated_analysis,
                    is_lemma=is_lemma,
                    pos=generated_pos.value,
                    lc=generated_lc.value,
                    as_is=False,
                )
                for english_keywords in engcrk_cree_to_keywords[
                    EngcrkCree(generated_inflection, generated_pos)
                ]:
                    db_keywords.append(
                        EnglishKeyword(
                            id=keyword_counter,
                            text=english_keywords,
                            lemma=db_inflection,
                        )
                    )

                    keyword_counter += 1

                if i == 0:
                    default_spelling = db_inflection
                db_inflection.default_spelling = default_spelling
                db_inflections_for_analysis.append(db_inflection)
                inflection_counter += 1
                db_inflections.append(db_inflection)

                if is_lemma:
                    db_lemmas.append(db_inflection)

            if is_lemma:
                for db_lemma in db_lemmas:
                    str_definitions_source_strings = xml_lemma_pos_lc_to_str_definitions[
                        xml_lemma_pos_lcs[0]
                    ]

                    for (
                        str_definition,
                        source_strings,
                    ) in str_definitions_source_strings.items():
                        db_definition = Definition(
                            id=definition_counter, text=str_definition, lemma=db_lemma
                        )
                        assert definition_counter not in citations
                        citations[definition_counter] = set(source_strings)

                        definition_counter += 1
                        db_definitions.append(db_definition)

        for inflection in db_inflections_for_analysis:
            inflection.lemma = db_lemmas[0]

    logger.info("Inserting %d inflections to database..." % len(db_inflections))
    Inflection.objects.bulk_create(db_inflections)
    logger.info("Done inserting.")

    logger.info("Inserting definition to database...")
    Definition.objects.bulk_create(db_definitions)
    logger.info("Done inserting.")

    logger.info("Inserting citations [definition -> dictionary source] to database...")
    # ThroughModel is the "hidden" model that manages the Many-to-Many
    # relationship
    ThroughModel = Definition.citations.through

    def _generate_through_models():
        "Yields all associations between Definitions and DictionarySources"
        for dfn_id, src_ids in citations.items():
            for src_pk in src_ids:
                yield ThroughModel(definition_id=dfn_id, dictionarysource_id=src_pk)

    ThroughModel.objects.bulk_create(_generate_through_models())
    logger.info("Done inserting.")

    logger.info("Inserting English keywords to database...")
    EnglishKeyword.objects.bulk_create(db_keywords)
    logger.info("Done inserting.")

    seconds = datetime.timedelta(seconds=time.time() - start_time).seconds

    logger.info(
        f"{Fore.GREEN}Import finished in %d min %d sec{Fore.RESET}"
        % (seconds // 60, seconds % 60)
    )
