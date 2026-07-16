from pydantic import BaseModel
from typing import Optional


class NotificationLogCreate(BaseModel):
    template_id: Optional[int] = None
    recipient: str
    notification_type: str
    subject: Optional[str] = None
    message: Optional[str] = None
    status: Optional[int] = 1


class NotificationLogUpdate(BaseModel):
    template_id: Optional[int] = None
    recipient: Optional[str] = None
    notification_type: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None
    status: Optional[int] = None


class NotificationLogDelete(BaseModel):
    id: int