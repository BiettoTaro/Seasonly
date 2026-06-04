from enum import StrEnum


class StorageBackendType(StrEnum):
    POSTGRES = "postgres"
    MEMORY = "memory"
    RAW_FILE = "raw_file"
