from django.apps import AppConfig


class RanConfig(AppConfig):
    name = "main.apps.ran"
    label = "ran"

    def ready(self) -> None:  # noqa: D401
        # Register signals here if needed later.
        pass
