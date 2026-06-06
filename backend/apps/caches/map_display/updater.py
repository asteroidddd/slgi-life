from __future__ import annotations

from django.db import connection, transaction


MEDICAL_HOSPITAL_TYPES = (
    "의원",
    "병원",
    "종합병원",
    "한의원",
    "한방병원",
    "보건소",
)
MEDICAL_DENTAL_TYPES = ("치과의원", "치과병원")
MEDICAL_PHARMACY_TYPES = ("약국",)


def _sql_values(items: tuple[str, ...]) -> str:
    return ", ".join("'%s'" % item.replace("'", "''") for item in items)


def rebuild_map_amenity_marker_cache() -> int:
    """Rebuild amenity marker cache, excluding the broad etc bucket."""

    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE map_amenity_marker_cache")
        cursor.execute(
            """
            INSERT INTO map_amenity_marker_cache (
                id,
                category,
                name,
                location,
                updated_at
            )
            SELECT
                id,
                category,
                name,
                location,
                NOW()
            FROM amenity
            WHERE location IS NOT NULL
              AND category <> 'etc'
            """
        )
        return cursor.rowcount


def rebuild_map_medical_marker_cache() -> int:
    """Rebuild medical marker cache with regular hours and specialty groups."""

    dental_types = _sql_values(MEDICAL_DENTAL_TYPES)
    pharmacy_types = _sql_values(MEDICAL_PHARMACY_TYPES)
    hospital_types = _sql_values(MEDICAL_HOSPITAL_TYPES)

    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute("TRUNCATE TABLE map_medical_marker_cache")
        cursor.execute(
            f"""
            INSERT INTO map_medical_marker_cache (
                hpid,
                category,
                type,
                name,
                address,
                tel1,
                location,
                is_emergency,
                hours_summary,
                specialty_groups,
                updated_at
            )
            SELECT
                f.hpid,
                CASE
                    WHEN e.hpid IS NOT NULL THEN 'emergency'
                    WHEN f.type IN ({dental_types}) THEN 'dental'
                    WHEN f.type IN ({pharmacy_types}) THEN 'pharmacy'
                    WHEN f.type IN ({hospital_types}) THEN 'hospital'
                    ELSE 'hospital'
                END AS category,
                f.type,
                f.name,
                COALESCE(f.address, ''),
                COALESCE(f.tel1, ''),
                f.location,
                (e.hpid IS NOT NULL) AS is_emergency,
                COALESCE(h.hours_summary, '{{}}'::jsonb),
                COALESCE(s.specialty_groups, '[]'::jsonb),
                NOW()
            FROM medical_facility f
            LEFT JOIN medical_emergency e ON e.hpid = f.hpid
            LEFT JOIN (
                SELECT
                    hpid,
                    jsonb_object_agg(
                        day_type,
                        jsonb_build_object(
                            'open_time', open_time::text,
                            'close_time', close_time::text,
                            'is_closed', is_closed
                        )
                    ) AS hours_summary
                FROM medical_facility_hours
                GROUP BY hpid
            ) h ON h.hpid = f.hpid
            LEFT JOIN (
                SELECT
                    hm.hpid,
                    COALESCE(
                        jsonb_agg(DISTINCT s.specialty_group)
                            FILTER (WHERE s.specialty_group <> ''),
                        '[]'::jsonb
                    ) AS specialty_groups
                FROM medical_hira_mapping hm
                LEFT JOIN medical_facility_specialty s
                    ON s.hira_ykiho = hm.hira_ykiho
                GROUP BY hm.hpid
            ) s ON s.hpid = f.hpid
            WHERE f.location IS NOT NULL
            """
        )
        return cursor.rowcount
