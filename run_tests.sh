#!/bin/bash
docker compose run --rm -e DJANGO_SETTINGS_MODULE=core.test_settings web python manage.py test "$@"
