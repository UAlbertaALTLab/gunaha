from django.shortcuts import render

from apps.morphodict.models import Head


def index(request):
    terms = search_entries()[:100]
    return render(request, "gunaha/index.html", context={"terms": terms})


def search_entries():
    return Head.objects.all().prefetch_related("definitions")
