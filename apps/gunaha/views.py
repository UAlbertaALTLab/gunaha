from functools import lru_cache as call_and_cache
from pathlib import Path

from django.core.paginator import Paginator
from django.http import Http404
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
    """
    A page in templates/gunana/pages/*.html will be served by this template:
    """
    if page_name not in find_available_pages():
        # This is not a page we can serve.
        raise Http404

    return render(request, f"gunaha/pages/{page_name}.html")


@call_and_cache
def find_available_pages():
    """
    Searches for available HTML templates in Gunaha's template dir.
    """
    pages_directory = Path(__file__).parent / "templates" / "gunaha" / "pages"
    assert pages_directory.is_dir(), pages_directory
    return {name.stem for name in pages_directory.glob("*.html")}
