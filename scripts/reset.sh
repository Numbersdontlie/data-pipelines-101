#!/bin/bash
# reset.sh — Tear down and rebuild the entire playground
# Usage: bash scripts/reset.sh [--keep-data]

set -e

KEEP_DATA=false
if [[ "$1" == "--keep-data" ]]; then
  KEEP_DATA=true
fi

echo ""
echo "🔄 Data Engineering Playground — Reset"
echo "======================================="

if [ "$KEEP_DATA" = false ]; then
  echo "⚠️  This will DELETE all data volumes. Press Ctrl+C to cancel."
  sleep 3
  echo "Stopping and removing containers + volumes..."
  docker compose down -v --remove-orphans
else
  echo "Stopping containers (keeping data volumes)..."
  docker compose down --remove-orphans
fi

echo ""
echo "🚀 Starting fresh stack..."
docker compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 15

echo ""
echo "🌱 Seeding sample data..."
docker compose exec -T airflow-webserver python /opt/airflow/scripts/seed_data.py

echo ""
echo "✅ Playground is ready!"
echo ""
echo "  pgAdmin  → http://localhost:5050  (admin@playground.dev / playground)"
echo "  Airflow  → http://localhost:8080  (admin / admin)"
echo "  Superset → http://localhost:8088  (admin / admin)"
echo ""
echo "Run the pipeline:"
echo "  docker compose exec airflow-webserver airflow dags trigger medallion_pipeline"
