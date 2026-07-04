from enum import StrEnum


class LocationSource(StrEnum):
    DEVICE = "device"
    MANUAL = "manual"
    COARSE_HEADER = "coarse_header"
