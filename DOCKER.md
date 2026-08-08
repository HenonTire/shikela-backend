# Docker Setup Guide

This project is configured to run with Docker for both local development and production deployment.

## Prerequisites

- Docker Engine (v20.10+)
- Docker Compose (v2.0+)
- At least 4GB of available RAM

## Quick Start (Development)

### 1. Prepare Environment
```bash
cp .env.docker .env
# Or for local non-Docker development:
# cp .env.example .env
```

### 2. Build and Start Services
```bash
docker compose up -d
```

Optional nginx reverse proxy (port 8080 by default):
```bash
docker compose --profile nginx up -d
```

This will:
- Build the Django application image
- Start PostgreSQL database
- Start Redis cache/broker
- Start Celery worker
- Start Celery Beat scheduler
- Run migrations automatically
- Collect static files
- Start the Django application on http://localhost:8000

### 3. Create Superuser
```bash
docker-compose exec web python manage.py createsuperuser
```

### 4. Access the Application
- API: http://localhost:8000
- Admin Panel: http://localhost:8000/admin

## Common Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f db
```

### Run Django Management Commands
```bash
docker-compose exec web python manage.py <command>
```

### Stop Services
```bash
docker-compose down
```

### Full Cleanup (includes volumes)
```bash
docker-compose down -v
```

### Rebuild Images
```bash
docker-compose build --no-cache
```

## Service Details

### PostgreSQL (Port 5432)
- User: `shikela_user`
- Password: `shikela_password`
- Database: `shikela_db`
- Volume: `postgres_data`

### Redis (Port 6379)
- Default database used for Celery broker and cache
- Volume: `redis_data`

### Django Web (Port 8000)
- Gunicorn WSGI server with 4 workers
- Hot-reload enabled for development
- Automatic migration on startup
- Volume: `.` (project root for development)

### Celery Worker
- Processes async tasks
- Depends on Redis and PostgreSQL

### Celery Beat
- Scheduled task scheduler
- Depends on Redis and PostgreSQL

## Environment Variables

Key environment variables (see `.env.example` and `.env.docker`):

- `DEBUG`: Debug mode (True/False)
- `DJANGO_SECRET_KEY`: Django secret key
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `CELERY_BROKER_URL`: Celery broker URL

## Production Deployment

### Build for Production
```bash
docker build -t shikela-backend:latest .
```

### Push to Registry
```bash
docker tag shikela-backend:latest your-registry/shikela-backend:latest
docker push your-registry/shikela-backend:latest
```

### Environment Configuration
Update `.env` with production values:
- Set `DEBUG=False`
- Use strong `DJANGO_SECRET_KEY`
- Configure `ALLOWED_HOSTS` properly
- Use external PostgreSQL and Redis services
- Configure email settings for production
- Update all third-party API credentials

### Run with External Services
Modify `docker-compose.yml` or create `docker-compose.prod.yml` to connect to external databases.

## Troubleshooting

### Database Connection Errors
```bash
# Check database service health
docker-compose exec db pg_isready -U shikela_user

# Check logs
docker-compose logs db
```

### Redis Connection Errors
```bash
# Test Redis connection
docker-compose exec redis redis-cli ping

# Check Redis logs
docker-compose logs redis
```

### Static Files Not Loading
```bash
# Re-collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Permission Denied on entrypoint.sh
```bash
chmod +x entrypoint.sh
docker-compose build --no-cache
```

### Port Already in Use
Change port mappings in `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"  # Maps host port 8001 to container port 8000
```

## Health Checks

All services have health checks configured:
- PostgreSQL: Checks if `pg_isready`
- Redis: Checks if it responds to `PING`
- Web: Checks HTTP health endpoint (basic check)

Monitor health status:
```bash
docker-compose ps
```

## Development Tips

### Hot Reload for Code Changes
The web service has volume mapping for the project root, so code changes are reflected immediately without rebuilding.

### Run Tests
```bash
docker-compose exec web python manage.py test
```

### Database Shell
```bash
docker-compose exec db psql -U shikela_user -d shikela_db
```

### Python Shell
```bash
docker-compose exec web python manage.py shell
```

### Interactive Debugging
Add breakpoint in code:
```python
breakpoint()
```

Then:
```bash
docker-compose exec web python manage.py runserver 0.0.0.0:8000
```

## Security Notes

- Change default PostgreSQL credentials in `.env` before production
- Use strong `DJANGO_SECRET_KEY` for production
- Keep Docker images updated
- Scan images for vulnerabilities: `docker scan`
- Use secrets management for sensitive data in production
- Set `DEBUG=False` in production

## Support

For issues or questions, check:
1. Docker logs: `docker-compose logs`
2. Service health: `docker-compose ps`
3. Environment variables: `.env` file
4. Django debug output in web service logs
