"""Simple offset pagination for list pages."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Pagination:
    page: int
    per_page: int
    total: int

    @classmethod
    def from_request(cls, raw_page, total: int, per_page: int = 25) -> "Pagination":
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            page = 1
        pages = max(1, total // per_page)
        return cls(page=min(max(page, 1), pages), per_page=per_page, total=total)

    @property
    def pages(self) -> int:
        return max(1, self.total // self.per_page)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.per_page

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages
