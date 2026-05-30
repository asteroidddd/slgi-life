from django.db import migrations


def drop_index(name: str) -> migrations.RunSQL:
    return migrations.RunSQL(
        f'DROP INDEX CONCURRENTLY IF EXISTS "{name}"',
        reverse_sql=migrations.RunSQL.noop,
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("regions", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                drop_index("gu_boundary_gist_idx"),
                drop_index("ldong_gu_code_af3dfe_idx"),
                drop_index("ldong_boundary_gist_idx"),
                drop_index("adong_boundary_gist_idx"),
                drop_index("adjacent_gu_gu1_cod_11c194_idx"),
                drop_index("adjacent_gu_gu2_cod_ccdc76_idx"),
                drop_index("adjacent_ld_ldong1__a4b139_idx"),
                drop_index("adjacent_ld_ldong2__08c33b_idx"),
                drop_index("adjacent_ad_adong1__7a7873_idx"),
                drop_index("adjacent_ad_adong2__8155e5_idx"),
            ],
            state_operations=[
                migrations.RemoveIndex(model_name="gu", name="gu_boundary_gist_idx"),
                migrations.RemoveIndex(model_name="ldong", name="ldong_gu_code_af3dfe_idx"),
                migrations.RemoveIndex(model_name="ldong", name="ldong_boundary_gist_idx"),
                migrations.RemoveIndex(model_name="adong", name="adong_boundary_gist_idx"),
                migrations.RemoveIndex(model_name="guadjacency", name="adjacent_gu_gu1_cod_11c194_idx"),
                migrations.RemoveIndex(model_name="guadjacency", name="adjacent_gu_gu2_cod_ccdc76_idx"),
                migrations.RemoveIndex(model_name="ldongadjacency", name="adjacent_ld_ldong1__a4b139_idx"),
                migrations.RemoveIndex(model_name="ldongadjacency", name="adjacent_ld_ldong2__08c33b_idx"),
                migrations.RemoveIndex(model_name="adongadjacency", name="adjacent_ad_adong1__7a7873_idx"),
                migrations.RemoveIndex(model_name="adongadjacency", name="adjacent_ad_adong2__8155e5_idx"),
            ],
        )
    ]
