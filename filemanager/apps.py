from django.apps import AppConfig


class FilemanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'filemanager'
    verbose_name = 'Управління файлами'

    def ready(self):
        import filemanager.signals  # noqa
