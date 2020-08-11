from typing import Optional

from django.core.paginator import Paginator
from django.shortcuts import render
from haystack.inputs import AutoQuery  # type: ignore
from haystack.query import SearchQuerySet  # type: ignore

from apps.morphodict.models import Head

from .orthography import to_search_form

MAX_RESULTS_PER_PAGE = 30


def index(request):
    results = search_entries(request.GET.get("q", None))
    pages = Paginator(results, MAX_RESULTS_PER_PAGE)
    # page page get page page get get get page get
    page = pages.get_page(request.GET.get("page", 1))
    return render(request, "gunaha/index.html", context={"page": page},)


def search_entries(query: Optional[str]):
    """
    Results are ALWAYS ordered!
    """

    query_set = SearchQuerySet().models(Head)

    if query is None:
        return query_set

    return query_set.filter(content=AutoQuery(query)) | query_set.filter(
        head__startswith=to_search_form(query)
    )
