from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_request_service.mq import producer as _mq_producer

if TYPE_CHECKING:
    from cityservices_request_service.models.request_db.service_request import (
        ServiceRequest,
    )


async def _request_db_service_request_after_update(
    target: ServiceRequest,
    db: AsyncSession,
    old_values: dict[str, object] | None = None,
    _commit: bool = True,
) -> None:
    """Execute afterUpdate lifecycle hook for ServiceRequest."""
    from cityservices_request_service.services._base import (
        _field_changed,
        _field_old_value,
    )

    if _field_changed(target, "status", old_values):
        _producer_instance = await _mq_producer.get_producer()
        await _producer_instance.publish_request_status_changed(
            target.id,
            target.request_number,
            _field_old_value(target, "status", old_values),
            target.status,
        )
