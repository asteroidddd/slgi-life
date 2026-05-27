"""SLGI step 7G-B1: legacy `AdongAdmin` 제거.

기존 `neighborhoods.Adong` 모델은 7G-C에서 제거 예정 (사용자 결정 5A — neighborhoods
빈 앱 유지). admin 등록은 신규 마스터인 regions.Adong (apps.public_data.regions.admin
에서 이미 등록) 으로 이관되었으므로 본 admin 파일은 빈 상태로 유지한다.
"""

# 의도적으로 비움. apps.public_data.regions.admin.AdongAdmin 사용.
