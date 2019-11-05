"""
fill a paradigm table according to a lemma
"""
import csv
import glob
from copy import deepcopy
from os import path
from os.path import dirname
from pathlib import Path
from typing import Dict, List, Tuple

import hfstol

from constants import LC, ParadigmSize
from paradigm import Layout, StaticCell, Table, rows_to_layout

LayoutID = Tuple[LC, ParadigmSize]


def import_prefilled_layouts(layout_file_dir: Path) -> Dict[LayoutID, Layout]:
    """

    """
    layout_tables = {}

    for layout_file in layout_file_dir.glob("*.tsv"):
        name_wo_extension = layout_file.stem
        ic_str, size_str = name_wo_extension.split("-")
        lc = LC(ic_str.upper())
        size = ParadigmSize(size_str.upper())

        with open(layout_file, "r") as f:
            reader = csv.reader(f, delimiter="\t", quotechar="'")
            # TODO: convert the raw layout into a normal layout
            layout = rows_to_layout(reader)
        layout_tables[(lc, size)] = layout

    return layout_tables


class ParadigmFiller:
    _layout_tables: Dict[LayoutID, Layout]

    def __init__(self, layout_dir: Path, generator_hfstol_path: Path):
        """
        reads all of .tsv layout files into memory.
        inits fst generator

        :param layout_dir: the directory for useful.layout.tsv files
        """
        self._layout_tables = import_prefilled_layouts(layout_dir)
        self._generator = hfstol.HFSTOL.from_file(generator_hfstol_path)

    @classmethod
    def default_filler(cls):
        """
        Return a filler that uses prefilled layout files and fst from the res folder
        """
        res = Path(dirname(__file__)) / ".." / "res"
        return ParadigmFiller(
            res / "prefilled_layouts", res / "fst" / "crk-normative-generator.hfstol"
        )

    def fill_paradigm(
        self, lemma: str, category: LC, paradigm_size: ParadigmSize
    ) -> List[Layout]:
        """
        returns a paradigm table filled with words

        :returns: filled paradigm tables
        """
        lookup_strings: List[str] = []
        string_locations: List[Tuple[int, int, int]] = []

        if category is LC.IPC or category is LC.Pron:
            return []

        layout_table = deepcopy(self._layout_tables[(category, paradigm_size)])

        tables: List[Layout] = [[]]

        table_index = 0
        row_index = 0

        for row in layout_table:
            # TODO: empty row
            if not any(row):
                tables.append([])
                table_index += 1
                row_index = 0
            else:
                tables[-1].append(row.copy())
                for colInd, cell in enumerate(row):
                    if isinstance(cell, StaticCell) or cell == "":
                        # We do nothing to static and empty cells.
                        continue

                    # It's a inflection form pattern
                    assert '"' not in cell
                    lookup_strings.append(cell.replace("{{ lemma }}", lemma))
                    string_locations.append((table_index, row_index, colInd))

                row_index += 1

        results = self._generator.feed_in_bulk_fast(lookup_strings)

        for i, locations in enumerate(string_locations):
            table_index, row_ind, col_ind = locations
            tables[table_index][row_ind][col_ind] = " / ".join(
                sorted(results[lookup_strings[i]])
            )

        return tables
