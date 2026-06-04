from app.data.data_key import UserDataKey
from app.data.enums import StorageBackendType
from app.data.schemas import DataSpec, DataTarget, UserProfileResponse

USER_PROFILE_TARGET = DataTarget(
    key=UserDataKey.PROFILE,
    spec=DataSpec(
        type=UserProfileResponse,
        backend=StorageBackendType.POSTGRES,
        enable_memory_cache=True,
    ),
)
