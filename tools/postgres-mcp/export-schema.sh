#!/usr/bin/env bash

set -euo pipefail

DB_NAME="${DB_NAME:-}"
DB_USER="${DB_USER:-}"
OUTFILE="${1:-tools/postgres-mcp/db-schema.sql}"

if [[ -z "$DB_NAME" || -z "$DB_USER" ]]; then
    echo "DB_NAME and DB_USER must be set before running this script." >&2
    echo "Example: DB_NAME=mydb DB_USER=myuser bash tools/postgres-mcp/export-schema.sh" >&2
    exit 1
fi

mkdir -p "$(dirname "$OUTFILE")"

echo "-- === Tables and Columns ===" > "$OUTFILE"
psql -U "$DB_USER" -d "$DB_NAME" -Atc "
SELECT
  '-- Table: ' || table_name || E'\n-- Columns: ' ||
  string_agg(column_name || ' (' || data_type || ')', ', ' ORDER BY ordinal_position)
FROM information_schema.columns
WHERE table_schema = 'public'
GROUP BY table_name
ORDER BY table_name;" >> "$OUTFILE"

echo -e "\n-- === Foreign Keys ===" >> "$OUTFILE"
psql -U "$DB_USER" -d "$DB_NAME" -Atc "
SELECT
  '-- ' || tc.table_name || '.' || kcu.column_name || ' → ' || ccu.table_name || '.' || ccu.column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
ORDER BY tc.table_name;" >> "$OUTFILE"

echo -e "\n-- === Indexes ===" >> "$OUTFILE"
psql -U "$DB_USER" -d "$DB_NAME" -Atc "
SELECT
  '-- ' || t.relname || ': ' || i.relname ||
  CASE ix.indisunique WHEN true THEN ' (UNIQUE)' ELSE '' END ||
  ' on columns: ' || string_agg(a.attname, ', ' ORDER BY a.attname)
FROM pg_class t
JOIN pg_index ix ON t.oid = ix.indrelid
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
JOIN pg_namespace ns ON ns.oid = t.relnamespace
WHERE ns.nspname = 'public'
GROUP BY t.relname, i.relname, ix.indisunique
ORDER BY t.relname, i.relname;" >> "$OUTFILE"

echo -e "\n-- === JSONB Field Structures (sample-based) ===" >> "$OUTFILE"
psql -U "$DB_USER" -d "$DB_NAME" -Atc "
SELECT table_name, column_name
FROM information_schema.columns
WHERE data_type = 'jsonb' AND table_schema = 'public'
ORDER BY table_name, column_name;" |
while IFS='|' read -r table column; do
    if [[ -z "$table" ]]; then
        continue
    fi

    echo -e "\n-- $table.$column (jsonb) sample structure:" >> "$OUTFILE"
    psql -U "$DB_USER" -d "$DB_NAME" -Atc "
    WITH source_rows AS MATERIALIZED (
      SELECT \"$column\"
      FROM \"$table\"
      WHERE \"$column\" IS NOT NULL
        AND jsonb_typeof(\"$column\") IN ('object', 'array')
      LIMIT 500
    ),
    unnested_items AS (
      SELECT \"$column\" AS item FROM source_rows WHERE jsonb_typeof(\"$column\") = 'object'
      UNION ALL
      SELECT jsonb_array_elements(\"$column\") AS item FROM source_rows WHERE jsonb_typeof(\"$column\") = 'array'
    ),
    level_1_pairs AS (
      SELECT key, value
      FROM unnested_items, jsonb_each(item)
      WHERE item IS NOT NULL AND jsonb_typeof(item) = 'object'
    )
    SELECT DISTINCT path || '|' || is_expandable::text FROM (
      SELECT
        key AS path,
        (jsonb_typeof(value) IN ('object', 'array')) AS is_expandable
      FROM level_1_pairs
      UNION ALL
      SELECT
        p1.key || '.' || p2 AS path,
        false AS is_expandable
      FROM level_1_pairs p1, jsonb_object_keys(p1.value) p2
      WHERE jsonb_typeof(p1.value) = 'object'
      UNION ALL
      SELECT
        p1.key || '.' || p2 AS path,
        false AS is_expandable
      FROM level_1_pairs p1,
           jsonb_array_elements(p1.value) AS arr_item,
           jsonb_object_keys(arr_item) AS p2
      WHERE jsonb_typeof(p1.value) = 'array' AND jsonb_typeof(arr_item) = 'object'
    ) AS final_paths
    ORDER BY 1;" | awk '
      BEGIN { FS = "|"; }
      {
          split($1, parts, ".");
          parent = parts[1];
          is_parent_line = (length(parts) == 1);
          is_expandable = ($2 == "t");

          if (is_parent_line) {
              if (!processed_parents[parent]) {
                  if (is_expandable) {
                      print "--   - " parent ":";
                      processed_parents[parent] = 1;
                  } else {
                      print "--   - " parent;
                  }
              }
          } else {
              child = parts[2];
              if (!processed_parents[parent]) {
                  print "--   - " parent ":";
                  processed_parents[parent] = 1;
              }
              print "--     - " child;
          }
      }
    ' >> "$OUTFILE"
done

echo "Schema saved to: $OUTFILE"