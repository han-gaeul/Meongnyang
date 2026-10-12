"""반려동물 등록정보 조회 연동.

서버가 본인인증으로 확인된 보호자 이름·생년월일과 동물등록번호로 조회해,
일치하면 자동 승인한다. 사용자에게 주민번호를 받지 않는다.
계약 전에는 MockPetRegistry로 개발한다.
"""

from dataclasses import dataclass
from datetime import date

from django.conf import settings


@dataclass(frozen=True)
class RegistryResult:
    found: bool  # 등록번호 자체가 조회되는가
    owner_matched: bool = False  # 소유자 정보가 일치하는가
    name: str = ""
    breed: str = ""
    sex: str = ""  # "M" / "F"
    neutered: bool | None = None


class PetRegistry:
    name = "base"

    def lookup(self, registration_number: str, owner_name: str, owner_birth: date | None) -> RegistryResult:
        raise NotImplementedError


class MockPetRegistry(PetRegistry):
    """개발용 규칙.

    - 번호가 '0'으로 시작: 조회 안 됨 → 운영자 검토 대기
    - 번호가 '9'로 시작: 조회되지만 소유자 불일치 → 반려
    - 그 외: 일치 → 자동 승인
    """

    name = "mock"

    def lookup(self, registration_number, owner_name, owner_birth):
        if registration_number.startswith("0"):
            return RegistryResult(found=False)
        if registration_number.startswith("9"):
            return RegistryResult(found=True, owner_matched=False)
        return RegistryResult(
            found=True, owner_matched=True, name="콩이", breed="골든 리트리버", sex="M", neutered=True
        )


class CoconPetRegistry(PetRegistry):
    name = "cocon"

    def lookup(self, registration_number, owner_name, owner_birth):
        # TODO: 계약 후 쿠콘 반려동물 등록정보 조회 API로 구현
        raise NotImplementedError("쿠콘 연동은 계약 후 구현")


_REGISTRIES = {r.name: r for r in (MockPetRegistry, CoconPetRegistry)}


def get_pet_registry() -> PetRegistry:
    return _REGISTRIES[settings.PET_REGISTRY_PROVIDER]()
