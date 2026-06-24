from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db.models import IEMSPlacementNotificationLog
from app.utils.auth_helper import get_current_user
from app.utils.http_return_helper import returnException, returnSuccess

router = APIRouter()


def _notification_log_to_dict(log):
    return {
        "id": log.id,
        "template_id": log.template_id,
        "recipient": log.recipient,
        "notification_type": log.notification_type,
        "subject": log.subject,
        "message": log.message,
        "status": log.status,
    }


@router.get("/get_notification_logs")
def get_notification_logs(
    current_user: dict = Depends(get_current_user),
    org_id: int = Header(...),
    db: Session = Depends(get_db),
):
    try:
        logs = (
            db.query(IEMSPlacementNotificationLog)
            .filter(
                IEMSPlacementNotificationLog.org_id == org_id,
                IEMSPlacementNotificationLog.status == 1,
            )
            .all()
        )

        return returnSuccess(
            [_notification_log_to_dict(log) for log in logs]
        )

    except Exception as e:
        return returnException(str(e))