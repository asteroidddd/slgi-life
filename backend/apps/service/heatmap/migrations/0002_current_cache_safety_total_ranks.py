from django.db import migrations, models


RANK_FIELDS = ("rank_rent", "rank_amenity", "rank_transit", "rank_safety", "rank_total")
SCORE_FIELDS = ("score_safety", "score_total")


def add_columns(table: str, ranked: bool) -> str:
    parts = [
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS score_safety double precision NOT NULL DEFAULT 0;",
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS score_total double precision NOT NULL DEFAULT 0;",
        f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at timestamp with time zone NULL;",
    ]
    if ranked:
        parts.extend(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {field} integer NULL;"
            for field in RANK_FIELDS
        )
    return "\n".join(parts)


def drop_columns(table: str, ranked: bool) -> str:
    fields = ["score_safety", "score_total", "updated_at"]
    if ranked:
        fields.extend(RANK_FIELDS)
    return "\n".join(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {field};" for field in fields)


class Migration(migrations.Migration):
    dependencies = [
        ("heatmap", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(add_columns("current_seoul", ranked=False), drop_columns("current_seoul", ranked=False)),
                migrations.RunSQL(add_columns("current_gu", ranked=True), drop_columns("current_gu", ranked=True)),
                migrations.RunSQL(add_columns("current_ldong", ranked=True), drop_columns("current_ldong", ranked=True)),
                migrations.RunSQL(add_columns("current_adong", ranked=True), drop_columns("current_adong", ranked=True)),
            ],
            state_operations=[
                migrations.AddField("currentseoul", "score_safety", models.FloatField(default=0.0)),
                migrations.AddField("currentseoul", "score_total", models.FloatField(default=0.0)),
                migrations.AddField("currentseoul", "updated_at", models.DateTimeField(blank=True, null=True)),
                migrations.AddField("currentgu", "score_safety", models.FloatField(default=0.0)),
                migrations.AddField("currentgu", "score_total", models.FloatField(default=0.0)),
                migrations.AddField("currentgu", "updated_at", models.DateTimeField(blank=True, null=True)),
                migrations.AddField("currentldong", "score_safety", models.FloatField(default=0.0)),
                migrations.AddField("currentldong", "score_total", models.FloatField(default=0.0)),
                migrations.AddField("currentldong", "updated_at", models.DateTimeField(blank=True, null=True)),
                migrations.AddField("currentadong", "score_safety", models.FloatField(default=0.0)),
                migrations.AddField("currentadong", "score_total", models.FloatField(default=0.0)),
                migrations.AddField("currentadong", "updated_at", models.DateTimeField(blank=True, null=True)),
                *[
                    migrations.AddField(model, field, models.PositiveIntegerField(blank=True, null=True))
                    for model in ("currentgu", "currentldong", "currentadong")
                    for field in RANK_FIELDS
                ],
            ],
        ),
    ]
