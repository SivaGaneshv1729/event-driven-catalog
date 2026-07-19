cd e:\Dev\event-driven-catalog
git init

# Commit 1: Project configuration and environment setup
git add docker-compose.yml .env.example README.md .gitignore
git commit -m "chore: Setup project structure and configuration`n`nAdded docker-compose for services orchestration, environment template, and initial README documenting the architecture."

# Commit 2: Producer base setup
git add producer-service/manage.py producer-service/producer_service/ producer-service/Dockerfile producer-service/requirements.txt
git commit -m "feat(producer): Initialize Django project for producer service`n`nConfigured Dockerfile, basic Django structure, and installed required dependencies."

# Commit 3: Producer events API
git add producer-service/api/
git reset producer-service/api/tests/
git commit -m "feat(producer): Implement REST API for publishing events`n`nCreated ProductEventView, serializers for payload validation, and RabbitMQ publisher logic using pika."

# Commit 4: Consumer base setup
git add consumer-service/manage.py consumer-service/consumer_service/ consumer-service/Dockerfile consumer-service/requirements.txt consumer-service/entrypoint.sh
git commit -m "feat(consumer): Initialize Django project and MySQL configuration`n`nConfigured Dockerfile with MySQL dependencies, entrypoint script, and Django settings for DB connection."

# Commit 5: Consumer models and services
git add consumer-service/api/models.py consumer-service/api/services.py consumer-service/api/__init__.py consumer-service/api/apps.py consumer-service/api/admin.py
git commit -m "feat(consumer): Create Database models and services`n`nAdded Product and ProcessedEvent (idempotency) models, and logic to update the local JSON search index."

# Commit 6: Consumer background worker
git add consumer-service/api/management/
git commit -m "feat(consumer): Implement RabbitMQ consumer management command`n`nCreated a long-running Django command to consume events, process them idempotently, update DB, and route failures to DLQ."

# Commit 7: Consumer Search API
git add consumer-service/api/views.py consumer-service/api/urls.py
git commit -m "feat(consumer): Implement local search API endpoint`n`nAdded GET /api/products/search endpoint that queries the denormalized JSON search index."

# Commit 8: Tests
git add producer-service/api/tests/ producer-service/pytest.ini consumer-service/api/tests/ consumer-service/pytest.ini
git commit -m "test: Add unit and integration tests`n`nCreated comprehensive test suites for producer event publishing and consumer indexing/processing logic using pytest."

# Add any remaining untracked files
git add .
git commit -m "chore: Catch-up commit for any missed files"

# Set remote and try pushing
git remote add origin https://github.com/SivaGaneshv1729/event-driven-catalog.git
git branch -M main
git push -u origin main
