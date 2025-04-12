from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'projects'
    verbose_name = 'Управління проектами і завданнями'

    def ready(self):
        import projects.signals  # noqa
