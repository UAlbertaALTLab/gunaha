from django.contrib import admin

from .models import Definition, DictionarySource, Head

# Register your models here.
admin.site.register(Head)
admin.site.register(Definition)
admin.site.register(DictionarySource)
