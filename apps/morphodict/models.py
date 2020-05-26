from django.db import models

MAX_HEAD_LENGTH = 64
MAX_DEFINITION_LENGTH = 256


class Head(models.Model):
    """
    Any linguistic utterance that is defined. This can be:

        - a phrase
        - a morpheme
        - a wordform
            - a wordform that is a lemma
    """

    text = models.CharField(max_length=MAX_HEAD_LENGTH)


class Definition(models.Model):
    """
    One of several possible meanings for the head.
    """

    text = models.CharField(max_length=MAX_DEFINITION_LENGTH)
    defines = models.ForeignKey(
        Head, on_delete=models.CASCADE, related_name="definitions"
    )
