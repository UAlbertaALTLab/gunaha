from django.core.paginator import Paginator
from django.shortcuts import render

from apps.morphodict.models import Head

MAX_RESULTS_PER_PAGE = 30


def index(request):
    terms = search_entries()
    pages = Paginator(terms, MAX_RESULTS_PER_PAGE)
    # page page get page page get get get page get
    page = pages.get_page(request.GET.get("page", 1))
    return render(request, "gunaha/index.html", context={"page": page},)


def search_entries():
    """
    Results are ALWAYS ordered!
    """
    return Head.objects.all().prefetch_related("definitions")
