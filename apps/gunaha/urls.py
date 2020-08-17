#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from django.urls import path

from . import views

app_name = "gunaha"
urlpatterns = [
    path("", views.index, name="index"),
    path("<str:page_name>", views.generic_page, name="page"),
]
