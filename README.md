# Event-Driven Product Catalog Microservice

A scalable, event-driven backend microservice responsible for managing a product catalog and asynchronously updating a search index. This project demonstrates event-driven architecture (EDA) using Django (Python), RabbitMQ, and MySQL, with Docker containerization.

## Architecture Overview

The system consists of two main decoupled microservices communicating asynchronously via RabbitMQ:
1. **Producer Service**: A Django API that receives product events (Create, Update, Delete) and publishes them to a RabbitMQ message exchange.
2. **Consumer Service**: A Django application that includes a background worker and a search API. The worker continuously listens to the RabbitMQ queue, processing events idempotently, persisting data to MySQL, and updating a local JSON search index.

**Error Handling & Resilience**:
- The consumer uses a Dead Letter Queue (DLQ) in RabbitMQ to capture messages that fail processing after 3 retry attempts, ensuring no data loss and facilitating later debugging.

## Setup Instructions

Ensure you have Docker and Docker Compose installed.

1. Clone this repository (or navigate to the directory).
2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
3. Start the services using Docker Compose:
   ```bash
   docker-compose up -d --build
   ```
4. Verify that all containers (`mysql`, `rabbitmq`, `producer-service`, `consumer-service`) are running and healthy:
   ```bash
   docker-compose ps
   ```

## API Documentation

### Producer Service

**Endpoint**: `POST http://localhost:8000/api/products/events`

Publishes a product event to the message queue.

**Example Request (ProductCreated)**:
```bash
curl -X POST http://localhost:8000/api/products/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "ProductCreated",
    "product_id": "prod_123",
    "payload": {
      "name": "Wireless Earbuds",
      "description": "High-fidelity audio, noise-cancelling.",
      "price": 129.99,
      "stock": 100
    }
  }'
```

**Example Request (ProductUpdated)**:
```bash
curl -X POST http://localhost:8000/api/products/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "ProductUpdated",
    "product_id": "prod_123",
    "payload": {
      "price": 119.99,
      "stock": 80
    }
  }'
```

**Example Request (ProductDeleted)**:
```bash
curl -X POST http://localhost:8000/api/products/events \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "ProductDeleted",
    "product_id": "prod_123",
    "payload": {}
  }'
```

**Example Response**:
```json
{
  "status": "success",
  "message": "Event published",
  "event_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Consumer Service (Search)

**Endpoint**: `GET http://localhost:8001/api/products/search?q={query}`

Searches the local JSON index for products matching the query.

**Example Request**:
```bash
curl "http://localhost:8001/api/products/search/?q=earbuds"
```

**Example Response**:
```json
[
  {
    "id": "prod_123",
    "name": "Wireless Earbuds",
    "description": "High-fidelity audio, noise-cancelling.",
    "price": 119.99
  }
]
```

## Running Tests

Tests for both services can be run using Docker Compose.

**Test Producer Service**:
```bash
docker-compose exec producer-service pytest
```

**Test Consumer Service**:
```bash
docker-compose exec consumer-service pytest
```

*(Unit tests cover business logic, idempotency, search indexing, while integration tests verify database connections.)*
