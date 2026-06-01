from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("amenities", "0004_dedupe_indexes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="amenity",
            name="category",
            field=models.CharField(
                choices=[
                    ("convenience", "편의점"),
                    ("mart", "슈퍼마켓"),
                    ("daiso", "다이소"),
                    ("restaurant", "음식점"),
                    ("cafe", "카페"),
                    ("hospital", "병원"),
                    ("dental", "치과"),
                    ("pharmacy", "약국"),
                    ("pet", "반려동물"),
                    ("laundry", "세탁"),
                    ("beauty", "미용"),
                    ("oliveyoung", "올리브영"),
                    ("gym", "헬스장"),
                    ("nightlife", "주점"),
                    ("book_stationery", "서점/문구"),
                    ("study_cafe", "스터디카페/독서실"),
                    ("etc", "기타"),
                    ("park", "공원"),
                    ("library", "도서관"),
                    ("subway_station", "지하철역"),
                    ("bus_stop", "버스정류장"),
                ],
                help_text="Facility category",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="amenity",
            name="source_table",
            field=models.CharField(
                choices=[
                    ("store", "store"),
                    ("daiso_store", "daiso_store"),
                    ("medical_facility", "medical_facility"),
                    ("park", "park"),
                    ("library", "library"),
                    ("univ", "univ"),
                    ("subway_station", "subway_station"),
                    ("bus_stop", "bus_stop"),
                ],
                help_text="Source table name for the amenity row",
                max_length=30,
            ),
        ),
    ]
