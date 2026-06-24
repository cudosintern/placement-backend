from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import IEMSPlacementNotificationEventType
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess
from datetime import datetime
from app.api.v1.placement_module.notification_schema import NotificationEventTypeCreate
router = APIRouter()
from app.api.v1.placement_module.notification_schema import (
    NotificationEventTypeCreate,
    NotificationEventTypeUpdate,
)

def _event_type_to_dict(event):
    return {
        "id": event.id,
        "event_code": event.event_code,
        "event_name": event.event_name,
        "status": event.status,
    }

@router.get("/get_event_types")
def get_event_types(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        events = (
            db.query(IEMSPlacementNotificationEventType)
            .filter(
                IEMSPlacementNotificationEventType.org_id == org_id,
                IEMSPlacementNotificationEventType.status == 1,
            )
            .all()
        )

        return returnSuccess(
            [_event_type_to_dict(event) for event in events]
        )

    except Exception as e:
        return returnException(str(e))
    
@router.post("/add_event_type")
def add_event_type(
    data: NotificationEventTypeCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        event = IEMSPlacementNotificationEventType(
            event_code=data.event_code,
            event_name=data.event_name,
            status=data.status,
            org_id=org_id,
            created_by=user_id,
            create_date=datetime.now(),
        )

        db.add(event)
        db.commit()
        db.refresh(event)

        return returnSuccess(
            _event_type_to_dict(event)
        )

    except Exception as e:
        db.rollback()
        return returnException(str(e))
    
@router.put("/update_event_type/{event_id}")
def update_event_type(
    event_id: int,
    data: NotificationEventTypeUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        event = (
            db.query(IEMSPlacementNotificationEventType)
            .filter(IEMSPlacementNotificationEventType.id == event_id)
            .first()
        )

        if not event:
            return returnException("Event Type not found")

        if data.event_code is not None:
            event.event_code = data.event_code

        if data.event_name is not None:
            event.event_name = data.event_name

        if data.status is not None:
            event.status = data.status

        event.modified_by = user_id
        event.modify_date = datetime.now()

        db.commit()
        db.refresh(event)

        return returnSuccess(
            _event_type_to_dict(event)
        )

    except Exception as e:
        db.rollback()
        return returnException(str(e))