"""
shared (expensive) instances
"""

from ..utils import paradigm_filler as pf
from ..utils import shared_res_dir

paradigm_filler = pf.ParadigmFiller.default_filler()
