from django.apps import AppConfig


class GunahaConfig(AppConfig):
    name = "apps.gunaha"
    verbose_name = "Gúnahà"

    def ready(self) -> None:
        """
        Make sure the dictionary is imported!
        """

        from .import_dictionary import import_dictionary

        import_dictionary()
