from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"

class Rating(Enum):
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"

@dataclass
class Ticket:
    id: int
    user_id: int
    full_name: str
    room: str
    problem: str
    status: TicketStatus
    created_at: datetime
    closed_by: Optional[str] = None
    closed_at: Optional[datetime] = None
    admin_response: Optional[str] = None
    rating: Optional[int] = None
    feedback: Optional[str] = None

@dataclass
class BlockedUser:
    user_id: int
    blocked_by: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    blocked_at: Optional[datetime] = None
    reason: Optional[str] = None