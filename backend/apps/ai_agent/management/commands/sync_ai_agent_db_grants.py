from django.core.management.base import BaseCommand
from django.db import connection

from apps.ai_agent.db import AI_SCHEMA_EXCLUDED_TABLES, get_ai_model_table_names


class Command(BaseCommand):
    help = "Sync SELECT grants for the AI agent read-only database role."

    def add_arguments(self, parser):
        parser.add_argument("--role", default="agent_read")
        parser.add_argument("--apply", action="store_true", help="Apply GRANT/REVOKE statements.")

    def handle(self, *args, **options):
        role = options["role"]
        apply_changes = options["apply"]
        quote = connection.ops.quote_name

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """
            )
            public_tables = {row[0] for row in cursor.fetchall()}

            allowed = (set(get_ai_model_table_names()) & public_tables) - AI_SCHEMA_EXCLUDED_TABLES
            revoked = public_tables - allowed

            statements = []
            statements.append(f"REVOKE CREATE ON SCHEMA public FROM {quote(role)}")
            for table in sorted(revoked):
                statements.append(f"REVOKE SELECT ON TABLE public.{quote(table)} FROM {quote(role)}")
            for table in sorted(allowed):
                statements.append(f"GRANT SELECT ON TABLE public.{quote(table)} TO {quote(role)}")

            if apply_changes:
                for statement in statements:
                    cursor.execute(statement)

        mode = "applied" if apply_changes else "dry-run"
        self.stdout.write(self.style.SUCCESS(f"AI grants {mode}: allow={len(allowed)} revoke={len(revoked)} role={role}"))
        for table in sorted(allowed):
            self.stdout.write(f"ALLOW {table}")
        for table in sorted(revoked):
            self.stdout.write(f"REVOKE {table}")
