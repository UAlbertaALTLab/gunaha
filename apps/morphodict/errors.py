#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


class MorphoDictError(Exception):
    """
    The base class of all exceptions raised intentionally by the MorpoDict application.
    """


class InvalidLanguageError(MorphoDictError):
    """
    Raised whenever an API is called with an invalid language selected.
    """
