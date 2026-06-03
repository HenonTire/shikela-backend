#!/bin/bash

# Docker helper script for Shikela Backend

set -e

DOCKER_COMPOSE="docker-compose"

function help() {
    echo "Shikela Backend Docker Helper"
    echo ""
    echo "Usage: ./docker-helper.sh [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start              Start all services"
    echo "  stop               Stop all services"
    echo "  logs               View logs from all services"
    echo "  logs-web           View logs from web service"
    echo "  logs-db            View logs from database service"
    echo "  logs-redis         View logs from redis service"
    echo "  logs-celery        View logs from celery worker"
    echo "  build              Build Docker images"
    echo "  rebuild            Rebuild Docker images (no cache)"
    echo "  ps                 Show status of all services"
    echo "  shell              Open Django shell"
    echo "  migrate            Run Django migrations"
    echo "  createsuperuser    Create Django superuser"
    echo "  test               Run Django tests"
    echo "  clean              Remove containers and volumes"
    echo "  bash               Open bash in web container"
    echo "  dbshell            Open PostgreSQL shell"
    echo "  static             Collect static files"
    echo "  help               Show this help message"
}

function start() {
    echo "Starting services..."
    $DOCKER_COMPOSE up -d
    echo "Services started. Access at http://localhost:8000"
}

function stop() {
    echo "Stopping services..."
    $DOCKER_COMPOSE down
}

function logs() {
    $DOCKER_COMPOSE logs -f
}

function logs_web() {
    $DOCKER_COMPOSE logs -f web
}

function logs_db() {
    $DOCKER_COMPOSE logs -f db
}

function logs_redis() {
    $DOCKER_COMPOSE logs -f redis
}

function logs_celery() {
    $DOCKER_COMPOSE logs -f celery
}

function build() {
    echo "Building Docker images..."
    $DOCKER_COMPOSE build
}

function rebuild() {
    echo "Rebuilding Docker images (no cache)..."
    $DOCKER_COMPOSE build --no-cache
}

function ps() {
    $DOCKER_COMPOSE ps
}

function shell() {
    $DOCKER_COMPOSE exec web python manage.py shell
}

function migrate() {
    echo "Running migrations..."
    $DOCKER_COMPOSE exec web python manage.py migrate
}

function createsuperuser() {
    $DOCKER_COMPOSE exec web python manage.py createsuperuser
}

function test() {
    $DOCKER_COMPOSE exec web python manage.py test
}

function clean() {
    echo "Removing containers and volumes..."
    $DOCKER_COMPOSE down -v
}

function bash() {
    $DOCKER_COMPOSE exec web bash
}

function dbshell() {
    $DOCKER_COMPOSE exec db psql -U shikela_user -d shikela_db
}

function static() {
    echo "Collecting static files..."
    $DOCKER_COMPOSE exec web python manage.py collectstatic --noinput
}

# Main script logic
if [ $# -eq 0 ]; then
    help
    exit 0
fi

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    logs-web)
        logs_web
        ;;
    logs-db)
        logs_db
        ;;
    logs-redis)
        logs_redis
        ;;
    logs-celery)
        logs_celery
        ;;
    build)
        build
        ;;
    rebuild)
        rebuild
        ;;
    ps)
        ps
        ;;
    shell)
        shell
        ;;
    migrate)
        migrate
        ;;
    createsuperuser)
        createsuperuser
        ;;
    test)
        test
        ;;
    clean)
        clean
        ;;
    bash)
        bash
        ;;
    dbshell)
        dbshell
        ;;
    static)
        static
        ;;
    help)
        help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        help
        exit 1
        ;;
esac
