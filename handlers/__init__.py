from .common_handlers import common_router
from .user_handlers import user_router
from .admin_handlers import admin_router
from .rating_handlers import rating_router

__all__ = [
    'common_router',
    'user_router',
    'admin_router',
    'rating_router'
]