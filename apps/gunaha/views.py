from django.core.paginator import Paginator
from django.shortcuts import render

from apps.morphodict.search import search_entries

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


def generic_page(request, page_name):
    # TODO: assert the page exists!
    # TODO: 404 ortherwise
    return render(request, f"gunaha/pages/{page_name}.html")
