from django.shortcuts import render

from apps.morphodict.models import Head


def index(request):
    terms = Head.objects.all()
    return render(request, "gunaha/index.html", context={"terms": terms})
