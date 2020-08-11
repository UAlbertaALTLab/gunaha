from typing import Optional

from django.core.paginator import Paginator
from django.shortcuts import render
from haystack.query import EmptySearchQuerySet, SearchQuerySet  # type: ignore

from apps.morphodict.models import Head

from .orthography import to_search_form

MAX_RESULTS_PER_PAGE = 30


def index(request):
    query = request.GET.get("q", None)
    results = search_entries(query)
    pages = Paginator(results, MAX_RESULTS_PER_PAGE)
    # page page get page page get get get page get
    page = pages.get_page(request.GET.get("page", 1))
    return render(
        request,
        "gunaha/index.html",
        context={"page": page, "query": query, "paginator": pages},
    )


def search_entries(query: Optional[str]):
    """
    Results are ALWAYS ordered!
    """

    if query is None:
        query_set = EmptySearchQuerySet()
    else:
        query_set = SearchQuerySet().models(Head)

    text = query or ""
    return query_set.auto_query(text) | query_set.filter(
        head__startswith=to_search_form(text)
    )
