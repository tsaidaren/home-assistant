"""Light util functions."""


def brightness_to_percentage(brightness: float, base=100) -> int:
    """Convert brightness to 0..base to percentage."""
    return round(brightness * base / 255.0)


def percentage_to_brightness(percent: float, base=100) -> float:
    """Convert percentage to float that home assistant uses."""
    return percent * 255.0 / base
