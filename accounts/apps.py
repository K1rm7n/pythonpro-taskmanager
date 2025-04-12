from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
    verbose_name = 'Управління обліковими записами'

    def ready(self):
        import accounts.signals  # noqa
