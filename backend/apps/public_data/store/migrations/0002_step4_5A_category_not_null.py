"""sub-plan 4.5A — store 앱 BusinessCategory / KsciCategory 모델을 schema.dbml과 정합.

변경 요약 (DB 0행 가정):
- BusinessCategory : 5개 컬럼 NOT NULL (Char blank=False)
- KsciCategory     : 5개 컬럼 varchar(200) → varchar(100) + NOT NULL

Store 모델 자체는 4.5C(서비스 도메인 ETL/serializer 정합) 단계에서 처리한다.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0001_initial"),
    ]

    operations = [
        # BusinessCategory NOT NULL
        migrations.AlterField(
            model_name="businesscategory",
            name="subcategory_name",
            field=models.CharField(help_text="소분류명", max_length=100),
        ),
        migrations.AlterField(
            model_name="businesscategory",
            name="middle_category_code",
            field=models.CharField(help_text="중분류 코드", max_length=20),
        ),
        migrations.AlterField(
            model_name="businesscategory",
            name="middle_category_name",
            field=models.CharField(help_text="중분류명", max_length=100),
        ),
        migrations.AlterField(
            model_name="businesscategory",
            name="main_category_code",
            field=models.CharField(help_text="대분류 코드", max_length=20),
        ),
        migrations.AlterField(
            model_name="businesscategory",
            name="main_category_name",
            field=models.CharField(help_text="대분류명", max_length=100),
        ),
        # KsciCategory varchar(200→100) + NOT NULL
        migrations.AlterField(
            model_name="kscicategory",
            name="subcategory_name",
            field=models.CharField(help_text="소분류명", max_length=100),
        ),
        migrations.AlterField(
            model_name="kscicategory",
            name="class_name",
            field=models.CharField(help_text="세분류명", max_length=100),
        ),
        migrations.AlterField(
            model_name="kscicategory",
            name="subclass_name",
            field=models.CharField(help_text="세세분류명", max_length=100),
        ),
        migrations.AlterField(
            model_name="kscicategory",
            name="middle_category_name",
            field=models.CharField(help_text="중분류명", max_length=100),
        ),
        migrations.AlterField(
            model_name="kscicategory",
            name="main_category_name",
            field=models.CharField(help_text="대분류명", max_length=100),
        ),
    ]
