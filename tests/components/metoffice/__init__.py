"""Tests for the metoffice component."""

import datetime


class NewDateTime(datetime.datetime):
    """Patch time to a specific point."""

    @classmethod
    def now(cls, *args, **kwargs):
        """Overload datetime.datetime.now."""
        return cls(2020, 4, 25, 12, tzinfo=datetime.timezone.utc)
