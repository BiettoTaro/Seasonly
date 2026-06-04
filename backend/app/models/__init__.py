"""SQLAlchemy model package."""

from app.db.base import Base
from app.models.user import User, UserProfile

__all__ = ["Base", "User", "UserProfile"]
