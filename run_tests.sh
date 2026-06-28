#!/bin/bash
echo "Stopping celery..."
docker compose stop celery celery-beat

echo "Running tests..."
docker compose run --rm web python manage.py test --verbosity=2

echo "Terminating leftover test DB connections..."
docker compose exec db psql -U shikela_user -d shikela_db -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'test_shikela_db' AND pid <> pg_backend_pid();
"

echo "Restarting celery..."
docker compose start celery celery-beat