from enum import StrEnum


class DataTargetType(StrEnum):
    RAW_FILE = "raw_file"
    NORMALIZED_TABLE = "normalized_table"
    ML_FEATURE_SET = "ml_feature_set"
