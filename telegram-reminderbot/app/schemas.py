from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime


class Reminder(BaseModel):
    '''
    "reminder_id": "435217cc-9365-4d65-b887-b26a19fc0f2d",
    "user_id": 403682365,
    "reminder_text": "this is a reminder text with image",
    "file_id": "AgACAgUAAxkBAAIC4GF221tnj06qWnVCs_AHK-OHrdTNAALxrDEbQfOoV9HKf2nxxAjLAQADAgADeQADIQQ",
    "frequency": "Once 2021-12-12",
    "time": "12:45",
    "job_id": "2ecb00df-c653-4254-a0c9-b1e7b6f2f079"
    '''
    reminder_id: Optional[str]
    chat_id: int
    from_user_id: int
    reminder_text: str
    file_id: Optional[str]
    timezone: Optional[str]
    frequency: str
    time: str

    class Config():
        orm_mode = True
        schema_extra = {
            "example": {
                "chat_id": 403432365,
                "from_user_id": 403432365,
                "reminder_text": "This is a reminder",
                "file_id":
                "AgACAgUAAxkBAAIC4GF221tnj06qWnVCs_AHK-OHrdTNAALxrDEbQfOoV9HKf2nxxAjLAQADAgADeQADIQQ",
                "timezone": "Asia/Singapore",
                "frequency": "Once 2021-11-19",
                "time": "08:19"
            }
        }


class ShowReminder(Reminder):
    '''
    "reminder_id": "435217cc-9365-4d65-b887-b26a19fc0f2d",
    "user_id": 403682365,
    "reminder_text": "this is a reminder text with image",
    "file_id": "AgACAgUAAxkBAAIC4GF221tnj06qWnVCs_AHK-OHrdTNAALxrDEbQfOoV9HKf2nxxAjLAQADAgADeQADIQQ",
    "frequency": "Once 2021-12-12",
    "time": "12:45",
    "job_id": "2ecb00df-c653-4254-a0c9-b1e7b6f2f079"
    '''
    job_id: str

    class Config():
        orm_mode = True
        schema_extra = {
            "example": {
                "reminder_id": "435217cc-9365-4d65-b887-b26a19fc0f2d",
                "chat_id": 403432365,
                "from_user_id": 403432365,
                "reminder_text": "This is a reminder",
                "file_id":
                "AgACAgUAAxkBAAIC4GF221tnj06qWnVCs_AHK-OHrdTNAALxrDEbQfOoV9HKf2nxxAjLAQADAgADeQADIQQ",
                "timezone": "Asia/Singapore",
                "frequency": "Once 2021-12-12",
                "time": "12:30",
                "job_id": "2ecb00df-c653-4254-a0c9-b1e7b6f2f079"
            }
        }
