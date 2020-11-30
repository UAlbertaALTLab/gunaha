from django.contrib import admin

from .models import Definition, Head

# Register your models here.
admin.site.register(Head)
admin.site.register(Definition)
