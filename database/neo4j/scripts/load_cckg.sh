#!/usr/bin/env bash
# Idempotently load the CCKG schema and all seed cypher files into the dockerised Neo4j.
# Usage: bash database/neo4j/scripts/load_cckg.sh   (from the repo root, after `docker compose up -d neo4j`)
set -euo pipefail
CONTAINER="${NEO4J_CONTAINER:-adaptivelearnse-neo4j}"
USER="${NEO4J_USER:-neo4j}"
PASS="${NEO4J_PASSWORD:-change-me-in-development}"
cd "$(dirname "$0")/../../.."
for f in database/neo4j/schema/*.cypher database/neo4j/cypher/*.cypher; do
  echo "Loading $f"
  docker exec -i "$CONTAINER" cypher-shell -u "$USER" -p "$PASS" < "$f"
done
docker exec "$CONTAINER" cypher-shell -u "$USER" -p "$PASS" \
  "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label"
