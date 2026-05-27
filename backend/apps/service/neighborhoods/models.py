"""
sub-plan 7G-C (결정 5A) — `Adong` 모델 폐기 완료.

기존 `Adong` (행정동, db_table='adong') 모델은 `regions.Adong` + 점수 합성으로
완전 대체되었다. neighborhoods 앱 자체는 빈 앱으로 유지한다 (결정 5A):
- summary / detail / explore / score_point / match / compare 등의 view·serializer
  계층은 본 앱에 그대로 남는다. 이들은 `adong_surface.build_adong_qs()`를 통해
  Adong + 합성 score 컬럼을 노출한다.
- 본 파일은 의도적으로 모델을 정의하지 않는다. `from apps.service.neighborhoods.models
  import Adong` import는 더 이상 동작하지 않으며, 그러한 호출은 모두 `regions.Adong`
  + `adong_surface.wrap()` 으로 치환되어야 한다.
"""

# 의도적으로 비움. apps.public_data.regions.models.Adong 사용.
