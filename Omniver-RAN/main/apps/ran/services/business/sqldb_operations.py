"""Generic SQL CRUD operations. MUST stay generic per backend_rule.md §5-3.

No Model-specific methods here. Actor決定 model_class。
"""
from __future__ import annotations

from typing import Any, Iterable

from django.db.models import Model, QuerySet


class SqlDbBusinessService:
    @staticmethod
    def create_entity(model_class: type[Model], validated_data: dict[str, Any]) -> Model:
        return model_class.objects.create(**validated_data)

    @staticmethod
    def get_entity(model_class: type[Model], **lookup: Any) -> Model:
        return model_class.objects.get(**lookup)

    @staticmethod
    def find_entity(model_class: type[Model], **lookup: Any) -> Model | None:
        return model_class.objects.filter(**lookup).first()

    @staticmethod
    def list_entities(
        model_class: type[Model],
        filters: dict[str, Any] | None = None,
        order_by: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[Model]:
        qs: QuerySet = model_class.objects.all()
        if filters:
            qs = qs.filter(**filters)
        if order_by:
            qs = qs.order_by(*order_by)
        if limit is not None:
            qs = qs[:limit]
        return list(qs)

    @staticmethod
    def update_entity(instance: Model, updates: dict[str, Any]) -> Model:
        for field, value in updates.items():
            setattr(instance, field, value)
        instance.save()
        return instance

    @staticmethod
    def delete_entity(instance: Model) -> None:
        instance.delete()

    @staticmethod
    def upsert_entity(
        model_class: type[Model],
        lookup: dict[str, Any],
        defaults: dict[str, Any],
    ) -> tuple[Model, bool]:
        """Returns (instance, created)."""
        return model_class.objects.update_or_create(defaults=defaults, **lookup)
