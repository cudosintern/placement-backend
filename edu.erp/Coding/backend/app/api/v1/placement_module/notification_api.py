from datetime import datetime

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.placement_models import (
    IEMSPlacementNotificationTemplate,
    IEMSPlacementNotificationLog,
)
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

from app.api.v1.placement_module.notification_schema import (
    NotificationCreate,
    NotificationUpdate,
    NotificationEngineRequest,
)

router = APIRouter()


def _notification_to_dict(n):
    return {
        "id": n.id,
        "notification_title": n.notification_title,
        "notification_message": n.notification_message,
        "notification_type": n.notification_type,
        "event_type_id": n.event_type_id,
        "status": n.status,
    }



@router.post("/add_notification_template")
def add_notification_template(
    data: NotificationCreate,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        notification = IEMSPlacementNotificationTemplate(
            notification_title=data.notification_title,
            notification_message=data.notification_message,
            notification_type=data.notification_type,
            event_type_id=data.event_type_id,
            status=data.status,
            org_id=org_id,
            created_by=user_id,
            create_date=datetime.now(),
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        return returnSuccess(
            _notification_to_dict(notification)
        )

    except Exception as e:
        db.rollback()
        return returnException(str(e))
    

@router.get("/get_notification_templates")
def get_notification_templates(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        notifications = (
            db.query(IEMSPlacementNotificationTemplate)
            .filter(
                IEMSPlacementNotificationTemplate.org_id == org_id,
                IEMSPlacementNotificationTemplate.status == 1,
            )
            .all()
        )

        return returnSuccess(
            [_notification_to_dict(n) for n in notifications]
        )
    except Exception as e:
        return returnException(str(e))

    
@router.put("/update_notification_template/{notification_id}")
def update_notification_template(
    notification_id: int,
    data: NotificationUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        notification = (
            db.query(IEMSPlacementNotificationTemplate)
            .filter(IEMSPlacementNotificationTemplate.id == notification_id)
            .first()
        )

        if not notification:
            return returnException("Notification Template not found")

        if data.notification_title is not None:
            notification.notification_title = data.notification_title

        if data.notification_message is not None:
            notification.notification_message = data.notification_message

        if data.notification_type is not None:
            notification.notification_type = data.notification_type
        
        if data.event_type_id is not None:
            notification.event_type_id = data.event_type_id

        if data.status is not None:
            notification.status = data.status

        notification.modified_by = user_id
        notification.modify_date = datetime.now()

        db.commit()
        db.refresh(notification)

        return returnSuccess(
            _notification_to_dict(notification)
        )

    except Exception as e:
        db.rollback()
        return returnException(str(e))

@router.delete("/delete_notification_template/{notification_id}")
def delete_notification_template(
    notification_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        notification = (
            db.query(IEMSPlacementNotificationTemplate)
            .filter(IEMSPlacementNotificationTemplate.id == notification_id)
            .first()
        )

        if not notification:
            return returnException("Notification Template not found")

        notification.status = 0
        notification.modified_by = user_id
        notification.modify_date = datetime.now()

        db.commit()

        return returnSuccess("Notification Template deleted successfully")

    except Exception as e:
        db.rollback()
        return returnException(str(e))
    
@router.post("/send_notification")
def send_notification(
    data: NotificationEngineRequest,
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("user_id")

        template = (
            db.query(IEMSPlacementNotificationTemplate)
            .filter(
                IEMSPlacementNotificationTemplate.id == data.template_id,
                IEMSPlacementNotificationTemplate.status == 1,
            )
            .first()
        )

        if not template:
            return returnException("Notification Template not found")

        log = IEMSPlacementNotificationLog(
            template_id=template.id,
            recipient=data.recipient,
            notification_type=template.notification_type,
            subject=template.notification_title,
            message=template.notification_message,
            status=1,
            org_id=org_id,
            created_by=user_id,
            create_date=datetime.now(),
        )

        db.add(log)
        db.commit()
        db.refresh(log)

        return returnSuccess("Notification sent successfully")

    except Exception as e:
        db.rollback()
        return returnException(str(e))