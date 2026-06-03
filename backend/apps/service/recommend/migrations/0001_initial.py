from django.db import migrations, models
import django.db.models.deletion


ADONG_TIME_SQL = """
INSERT INTO adong_univ_time (adong_code, univ_code, time)
SELECT
    a.adong_code,
    u.id AS univ_code,
    CEIL(ST_DistanceSphere(a.location, u.location) / 80.0)::integer AS time
FROM adong a
CROSS JOIN univ u
WHERE a.location IS NOT NULL
  AND u.location IS NOT NULL
ON CONFLICT (adong_code, univ_code) DO NOTHING;
"""

LDONG_TIME_SQL = """
INSERT INTO ldong_univ_time (ldong_code, univ_code, time)
SELECT
    l.ldong_code,
    u.id AS univ_code,
    CEIL(ST_DistanceSphere(l.location, u.location) / 80.0)::integer AS time
FROM ldong l
CROSS JOIN univ u
WHERE l.location IS NOT NULL
  AND u.location IS NOT NULL
ON CONFLICT (ldong_code, univ_code) DO NOTHING;
"""


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("regions", "0002_dedupe_indexes"),
        ("univ", "0002_dedupe_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdongUnivTime",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time", models.PositiveIntegerField(help_text="대학까지 예상 소요 시간(분)")),
                (
                    "adong",
                    models.ForeignKey(
                        db_column="adong_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="univ_times",
                        to="regions.adong",
                    ),
                ),
                (
                    "univ",
                    models.ForeignKey(
                        db_column="univ_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adong_times",
                        to="univ.univ",
                    ),
                ),
            ],
            options={
                "verbose_name": "행정동-대학 시간",
                "verbose_name_plural": "행정동-대학 시간",
                "db_table": "adong_univ_time",
            },
        ),
        migrations.CreateModel(
            name="LdongUnivTime",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("time", models.PositiveIntegerField(help_text="대학까지 예상 소요 시간(분)")),
                (
                    "ldong",
                    models.ForeignKey(
                        db_column="ldong_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="univ_times",
                        to="regions.ldong",
                    ),
                ),
                (
                    "univ",
                    models.ForeignKey(
                        db_column="univ_code",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ldong_times",
                        to="univ.univ",
                    ),
                ),
            ],
            options={
                "verbose_name": "법정동-대학 시간",
                "verbose_name_plural": "법정동-대학 시간",
                "db_table": "ldong_univ_time",
            },
        ),
        migrations.AddConstraint(
            model_name="adongunivtime",
            constraint=models.UniqueConstraint(fields=("adong", "univ"), name="uq_adong_univ_time"),
        ),
        migrations.AddConstraint(
            model_name="ldongunivtime",
            constraint=models.UniqueConstraint(fields=("ldong", "univ"), name="uq_ldong_univ_time"),
        ),
        migrations.AddIndex(
            model_name="adongunivtime",
            index=models.Index(fields=["univ", "time"], name="adong_univ_time_univ_idx"),
        ),
        migrations.AddIndex(
            model_name="adongunivtime",
            index=models.Index(fields=["adong"], name="adong_univ_time_adong_idx"),
        ),
        migrations.AddIndex(
            model_name="ldongunivtime",
            index=models.Index(fields=["univ", "time"], name="ldong_univ_time_univ_idx"),
        ),
        migrations.AddIndex(
            model_name="ldongunivtime",
            index=models.Index(fields=["ldong"], name="ldong_univ_time_ldong_idx"),
        ),
        migrations.RunSQL(
            sql=ADONG_TIME_SQL,
            reverse_sql="DELETE FROM adong_univ_time;",
        ),
        migrations.RunSQL(
            sql=LDONG_TIME_SQL,
            reverse_sql="DELETE FROM ldong_univ_time;",
        ),
    ]
