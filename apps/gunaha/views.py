from typing import Optional

from django.core.paginator import Paginator
from django.shortcuts import render

from apps.morphodict.models import Head

from .orthography import to_search_form

MAX_RESULTS_PER_PAGE = 30


def index(request):
    terms = search_entries(request.GET.get("q", None))
    pages = Paginator(terms, MAX_RESULTS_PER_PAGE)
    # page page get page page get get get page get
    page = pages.get_page(request.GET.get("page", 1))
    return render(request, "gunaha/index.html", context={"page": page},)


def search_entries(query: Optional[str]):
    """
    Results are ALWAYS ordered!
    """
    result_set = Head.objects.all()

    if query is not None:
        result_set = result_set.filter(text__istartswith=to_search_form(query))

    return result_set.prefetch_related("definitions")
