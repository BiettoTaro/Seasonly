from app.data.contracts import DataSpec, DataTarget, OnboardingProfileResponse, UserProfileResponse
from app.data.data_key import UserDataKey
from app.data.enums import StorageBackendType

USER_PROFILE_TARGET = DataTarget(
    key=UserDataKey.PROFILE,
    spec=DataSpec(
        type=UserProfileResponse,
        backend=StorageBackendType.POSTGRES,
        enable_memory_cache=True,
    ),
)

USER_ONBOARDING_PROFILE_TARGET = DataTarget(
    key=UserDataKey.ONBOARDING_PROFILE,
    spec=DataSpec(
        type=OnboardingProfileResponse,
        backend=StorageBackendType.POSTGRES,
        enable_memory_cache=True,
    ),
)
