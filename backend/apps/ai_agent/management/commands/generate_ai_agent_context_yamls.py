from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
from django.db import connection

from apps.ai_agent.db import (
    AI_SCHEMA_EXCLUDED_TABLES,
    DOMAIN_DICTIONARY_PATH,
    SCHEMA_CONTEXT_PATH,
    get_ai_model_table_names,
    get_ai_schema_table_names,
    get_table_metadata,
)


DOMAIN_TABLES = {
    "metric": {
        "description": "Metric codes, names, units, and interpretation hints.",
        "usage": "Use metric_code values directly in gu_metric and seoul_metric filters.",
        "columns": ["metric_code", "name", "unit", "category", "cycle", "is_generated"],
    },
    "ksci_category": {
        "description": "KSCI category reference values.",
        "usage": "Use for commercial/category interpretation when the table is present.",
    },
    "business_category": {
        "description": "Store business category code reference.",
        "usage": "Use subcategory_code with store.category_code. Prefer exact category codes over names.",
        "columns": [
            "main_category_code",
            "main_category_name",
            "middle_category_code",
            "middle_category_name",
            "subcategory_code",
            "subcategory_name",
        ],
    },
    "gu": {
        "description": "Seoul district codes and names.",
        "usage": "Use gu_code for district-level joins.",
        "columns": ["gu_code", "name"],
    },
    "adong": {
        "description": "Administrative neighborhood codes and names.",
        "usage": "Use adong_code for public_data/service administrative-dong joins.",
        "columns": ["adong_code", "name", "gu_code"],
    },
    "ldong": {
        "description": "Legal neighborhood codes and names.",
        "usage": "Use ldong_code for rent_deal and legal-dong joins.",
        "columns": ["ldong_code", "name", "gu_code"],
    },
    "univ": {
        "description": "University and campus names available to AI queries.",
        "usage": "Use university names with LIKE for school-nearby questions.",
        "columns": ["id", "name", "campus_name", "gu_code", "adong_code", "ldong_code"],
    },
}


METRIC_VALUE_GUIDANCE = {
    "SAFETY_GRADE": "Lower grade number is better. Use ASC for safer areas.",
    "ACC_": "Lower accident value is better. Prefer population-adjusted rates when available.",
    "TRAFFIC_CULTURE": "Higher score is better.",
    "POP_YOUTH_RATIO": "Higher value means more young residents.",
    "POP_ELDERLY_RATIO": "Higher value means older population share.",
    "POP_MEAN_AGE": "Higher value means older average age.",
    "AREA_GREEN": "Higher value means better green-space access or volume.",
    "LAND_PRICE_CHANGE_RATE": "Positive means land price increase; negative means decrease.",
    "HOUSING_PER_CAPITA": "Higher value means more housing per resident.",
    "GRDP": "Economic scale/reference only. Do not overuse as direct housing recommendation factor.",
}


class Command(BaseCommand):
    help = "Generate schema_context.yaml and domain_dictionary.yaml for the AI agent."

    def add_arguments(self, parser):
        parser.add_argument("--schema-output", default=str(SCHEMA_CONTEXT_PATH))
        parser.add_argument("--domain-output", default=str(DOMAIN_DICTIONARY_PATH))
        parser.add_argument("--domain-max-rows", type=int, default=2000)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        schema_output = Path(options["schema_output"])
        domain_output = Path(options["domain_output"])
        domain_max_rows = options["domain_max_rows"]
        dry_run = options["dry_run"]

        public_tables = self._get_public_tables()
        try:
            schema_tables = set(get_ai_schema_table_names())
        except Exception as exc:
            self.stderr.write(f"Falling back to model allowlist: {exc}")
            schema_tables = set(get_ai_model_table_names()) & public_tables
        schema_tables = (schema_tables & public_tables) - AI_SCHEMA_EXCLUDED_TABLES

        schema_data = self._build_schema_context(schema_tables)
        domain_data = self._build_domain_dictionary(schema_tables, domain_max_rows)

        if dry_run:
            self.stdout.write(f"schema_context tables={len(schema_data['tables'])}")
            self.stdout.write(f"domain_dictionary domains={len(domain_data['domains'])}")
            return

        schema_output.parent.mkdir(parents=True, exist_ok=True)
        domain_output.parent.mkdir(parents=True, exist_ok=True)
        self._write_yaml(schema_output, schema_data)
        self._write_yaml(domain_output, domain_data)

        self.stdout.write(self.style.SUCCESS(f"Wrote {schema_output}"))
        self.stdout.write(self.style.SUCCESS(f"Wrote {domain_output}"))

    def _get_public_tables(self) -> set[str]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                """
            )
            return {row[0] for row in cursor.fetchall()}

    def _build_schema_context(self, table_names: set[str]) -> dict[str, Any]:
        metadata = get_table_metadata()
        model_map = self._get_model_map()
        tables = {}

        with connection.cursor() as cursor:
            for table_name in sorted(table_names):
                table_meta = metadata.get(table_name, {})
                constraints = connection.introspection.get_constraints(cursor, table_name)
                columns = self._get_columns(cursor, table_name, constraints)
                foreign_keys = self._get_foreign_keys(constraints)
                indexes = self._get_indexes(constraints)
                model_info = model_map.get(table_name, {})

                tables[table_name] = {
                    "description": table_meta.get("description", ""),
                    "category": table_meta.get("category", ""),
                    "app_label": model_info.get("app_label", ""),
                    "model": model_info.get("model", ""),
                    "columns": columns,
                    "primary_key": [
                        column["name"] for column in columns if column.get("primary_key")
                    ],
                    "foreign_keys": foreign_keys,
                    "indexes": indexes,
                    "geometry_columns": [
                        column["name"]
                        for column in columns
                        if "geometry" in column.get("type", "").lower()
                        or column.get("name") in {"location", "boundary"}
                    ],
                    "join_hint": table_meta.get("join_path", ""),
                    "note": table_meta.get("note", ""),
                }

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Django introspection + AI schema allowlist + table_metadata.yaml",
            "tables": tables,
        }

    def _build_domain_dictionary(self, schema_tables: set[str], max_rows: int) -> dict[str, Any]:
        public_tables = self._get_public_tables()
        domains = {}
        with connection.cursor() as cursor:
            for table_name, spec in DOMAIN_TABLES.items():
                if table_name not in public_tables or table_name not in schema_tables:
                    continue
                columns = self._get_available_columns(cursor, table_name, spec.get("columns"))
                if not columns:
                    continue
                rows = self._fetch_rows(cursor, table_name, columns, max_rows)
                if table_name == "metric":
                    rows = [self._add_metric_guidance(row) for row in rows]
                domains[table_name] = {
                    "description": spec.get("description", ""),
                    "usage": spec.get("usage", ""),
                    "columns": columns,
                    "rows": rows,
                }

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "Database reference/domain tables",
            "domains": domains,
        }

    def _get_model_map(self) -> dict[str, dict[str, str]]:
        result = {}
        for model in django_apps.get_models():
            result[model._meta.db_table] = {
                "app_label": model._meta.app_label,
                "model": model.__name__,
            }
        return result

    def _get_columns(self, cursor, table_name: str, constraints: dict) -> list[dict[str, Any]]:
        primary_key_columns = {
            column
            for constraint in constraints.values()
            if constraint.get("primary_key")
            for column in constraint.get("columns", [])
        }
        fk_by_column = {
            constraint.get("columns", [""])[0]: (
                f"{constraint['foreign_key'][0]}.{constraint['foreign_key'][1]}"
            )
            for constraint in constraints.values()
            if constraint.get("foreign_key") and constraint.get("columns")
        }

        with connection.cursor() as column_cursor:
            column_cursor.execute(
                """
                SELECT column_name, data_type, udt_name, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                [table_name],
            )
            rows = column_cursor.fetchall()

        columns = []
        for name, data_type, udt_name, is_nullable, column_default in rows:
            column_type = udt_name if data_type == "USER-DEFINED" else data_type
            columns.append(
                {
                    "name": name,
                    "type": column_type,
                    "nullable": is_nullable == "YES",
                    "default": column_default or "",
                    "primary_key": name in primary_key_columns,
                    "foreign_key": fk_by_column.get(name, ""),
                }
            )
        return columns

    def _get_foreign_keys(self, constraints: dict) -> list[dict[str, str]]:
        result = []
        for constraint in constraints.values():
            if not constraint.get("foreign_key") or not constraint.get("columns"):
                continue
            result.append(
                {
                    "column": constraint["columns"][0],
                    "to_table": constraint["foreign_key"][0],
                    "to_column": constraint["foreign_key"][1],
                }
            )
        return result

    def _get_indexes(self, constraints: dict) -> list[dict[str, Any]]:
        result = []
        for name, constraint in constraints.items():
            if not constraint.get("index") and not constraint.get("unique"):
                continue
            result.append(
                {
                    "name": name,
                    "columns": constraint.get("columns", []),
                    "unique": bool(constraint.get("unique")),
                }
            )
        return result

    def _get_available_columns(self, cursor, table_name: str, preferred: list[str] | None) -> list[str]:
        cursor.execute(
            """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            [table_name],
        )
        rows = cursor.fetchall()
        available = [row[0] for row in rows]
        geometry_columns = {
            row[0]
            for row in rows
            if row[1] == "USER-DEFINED" and row[2] in {"geometry", "geography"}
        }
        if preferred:
            return [column for column in preferred if column in available]
        return [
            column
            for column in available
            if column not in geometry_columns and column not in {"location", "boundary"}
        ]

    def _fetch_rows(
        self,
        cursor,
        table_name: str,
        columns: list[str],
        max_rows: int,
    ) -> list[dict[str, Any]]:
        quote = connection.ops.quote_name
        selected_columns = ", ".join(quote(column) for column in columns)
        cursor.execute(
            f"SELECT {selected_columns} FROM {quote(table_name)} LIMIT %s",
            [max_rows],
        )
        rows = cursor.fetchall()
        return [
            {column: self._serialize_value(value) for column, value in zip(columns, row)}
            for row in rows
        ]

    def _add_metric_guidance(self, row: dict[str, Any]) -> dict[str, Any]:
        code = str(row.get("metric_code") or "")
        for prefix, guidance in METRIC_VALUE_GUIDANCE.items():
            if code.startswith(prefix):
                return {**row, "value_guidance": guidance}
        return row

    def _serialize_value(self, value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    def _write_yaml(self, path: Path, data: dict[str, Any]) -> None:
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
