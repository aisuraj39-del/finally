"""REST API routers."""

from . import chat, portfolio, system, watchlist

routers = [portfolio.router, watchlist.router, chat.router, system.router]

__all__ = ["routers"]
