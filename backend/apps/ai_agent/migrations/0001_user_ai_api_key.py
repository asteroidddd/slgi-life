from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserAIAPIKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("openai", "OpenAI"), ("mindlogic", "Mindlogic")], max_length=30)),
                ("priority", models.PositiveSmallIntegerField(default=1)),
                ("masked_key", models.CharField(blank=True, default="", max_length=255)),
                ("encrypted_api_key", models.TextField()),
                ("salt", models.CharField(max_length=128)),
                ("nonce", models.CharField(max_length=128)),
                ("tag", models.CharField(max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ai_api_keys", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "user_ai_api_key",
                "ordering": ["priority", "provider"],
                "unique_together": {("user", "provider")},
            },
        ),
        migrations.AddIndex(
            model_name="useraiapikey",
            index=models.Index(fields=["user", "priority"], name="user_ai_api_user_id_9a4e8d_idx"),
        ),
    ]
