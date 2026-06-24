# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from typing import Optional


class NotificationCreate(BaseModel):
    notification_title: str
    notification_message: str
    notification_type: str
    event_type_id: Optional[int] = None
    status: Optional[int] = 1

class NotificationUpdate(BaseModel):
    notification_title: Optional[str] = None
    notification_message: Optional[str] = None
    notification_type: Optional[str] = None
    event_type_id: Optional[int] = None
    status: Optional[int] = None


class NotificationDelete(BaseModel):
    id: int

class NotificationDelete(BaseModel):
    id: int


class NotificationEngineRequest(BaseModel):
    template_id: int
    recipient: str

class NotificationEventTypeCreate(BaseModel):
    event_code: str
    event_name: str
    status: Optional[int] = 1


class NotificationEventTypeUpdate(BaseModel):
    event_code: Optional[str] = None
    event_name: Optional[str] = None
    status: Optional[int] = None