"""REST API routers."""

from . import portfolio, system, watchlist

routers = [portfolio.router, watchlist.router, system.router]

__all__ = ["routers"]
