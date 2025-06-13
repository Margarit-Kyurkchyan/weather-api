# FastAPI Weather API Service

[![Python Version][python-badge]][python-link]
[![FastAPI][fastapi-badge]][fastapi-link]
[![Docker][docker-badge]][docker-link]
[![License: MIT][license-badge]][license-link]
[![Code style: black][black-badge]][black-link]

A production-ready, high-performance Weather API service built with FastAPI. This service fetches weather data from the OpenWeatherMap API, caches results, stores data in an S3-compatible object store (MinIO), and logs events to a NoSQL database (DynamoDB). The entire stack is containerized with Docker for seamless deployment and scalability.

## Project Overview

This project provides a robust RESTful API for retrieving weather information for a given city. It is designed with a microservices-oriented architecture, leveraging modern technologies to ensure reliability, performance, and scalability. The core application is written in Python using the async capabilities of FastAPI, making it highly efficient for I/O-bound operations like external API calls and database interactions.

## Key Features

- **Async FastAPI Application**: A high-performance, asynchronous API endpoint `/weather?city=<name>` for non-blocking I/O.
- **External API Integration**: Fetches real-time weather data from OpenWeatherMap, with robust error handling and API key management.
- **Cloud Storage Simulation**: Integrates with MinIO, an S3-compatible object storage service, to store JSON responses.
- **Database Logging**: Utilizes DynamoDB Local to log every API request and event for monitoring and auditing.
- **Intelligent Caching**: Implements a 5-minute in-memory cache to reduce latency and minimize redundant calls to the external API.
- **Dockerized Deployment**: Fully containerized with `docker compose` for consistent development, testing, and production environments.
- **Health & Monitoring**: Includes `/health` and `/stats` endpoints for service monitoring and usage statistics.
- **Production Ready**: Features structured logging, centralized configuration, comprehensive error handling, and a full test suite.

## Architecture

The service is composed of several containerized components orchestrated by `docker compose`:

1.  **FastAPI Application (`weather-api`)**: The core service that exposes the API endpoints. It handles incoming requests, orchestrates calls to other services, and manages the caching logic.
2.  **OpenWeatherMap**: The external source for weather data.
3.  **MinIO (`minio`)**: An S3-compatible object storage service used to archive the raw JSON weather data returned by the API.
4.  **DynamoDB (`dynamodb-local`)**: A local version of AWS DynamoDB used to store event logs, such as API requests and errors.
5.  **MinIO Initializer (`minio-init`)**: A one-off job that creates the required S3 bucket (`weather-data`) on startup.
6.  **DynamoDB Admin (`dynamodb-admin`)**: A web-based UI for viewing and managing the DynamoDB tables.

```
+-----------------+      +------------------------+      +------------------+
|      User       |----->|   FastAPI Service      |----->|  OpenWeatherMap  |
+-----------------+      |     (weather-api)      |      +------------------+
                         +------------------------+
                               |          |
                               |          |
      +------------------------v--+       v-------------------------+
      |  Cache (5-min TTL)        |       |  DynamoDB (Event Log)   |
      +---------------------------+       +-------------------------+
                               |
                               |
      +------------------------v--+
      |    MinIO (S3 Storage)     |
      +---------------------------+
```

---

## Quick Start Guide

Get the service running in under a minute.

**Prerequisites**:
*   [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/) are installed.
*   You have an [OpenWeatherMap API Key](https://openweathermap.org/appid).

**Steps**:
1.  **Clone the repository**:
    ```bash
    git clone <your-repo-url>
    cd weather-api
    ```

2.  **Configure Environment**:
    Copy the example environment file and add your OpenWeatherMap API key.
    ```bash
    cp .env.example .env
    ```
    Now, edit `.env` and set the `OPENWEATHERMAP_API_KEY`.

3.  **Start the Services**:
    Use the startup script to build and launch all containers.
    ```bash
    ./scripts/start.sh
    ```
    This script will run health checks and notify you when the API is ready.

4.  **Test the API**:
    ```bash
    curl "http://localhost:8000/weather?city=London"
    ```

## Detailed Setup Instructions

### 1. Prerequisites
- **Docker**: Ensure your Docker engine is running.
- **OpenWeatherMap API Key**: Sign up for a free account at [OpenWeatherMap](https://openweathermap.org/appid) to get an API key.

### 2. Configuration
The service is configured using environment variables defined in the `.env` file.

-   `OPENWEATHERMAP_API_KEY`: **(Required)** Your API key for OpenWeatherMap.
-   `CACHE_EXPIRATION_SECONDS`: Cache expiry time in seconds. Defaults to `300` (5 minutes).
-   `MINIO_URL`: MinIO server endpoint. Defaults to `http://minio:9000`.
-   `MINIO_ACCESS_KEY`: Access key for MinIO. Defaults to `minioadmin`.
-   `MINIO_SECRET_KEY`: Secret key for MinIO. Defaults to `minioadmin`.
-   `DYNAMODB_URL`: DynamoDB endpoint. Defaults to `http://dynamodb-local:8000`.

### 3. Ports
The `docker compose` stack exposes the following local ports:
-   `8000`: FastAPI Weather API
-   `9000`: MinIO API
-   `9001`: MinIO Console (Web UI)
-   `8001`: DynamoDB Admin (Web UI)

If these ports are in use on your local machine, you can change them in the `docker-compose.yml` file.

---

## API Usage

### Endpoints

#### 1. Get Weather Data
Fetches weather data for a specified city. Results are cached for 5 minutes.
-   **Endpoint**: `GET /weather?city=<name>`
-   **Example**:
    ```bash
    curl -X GET "http://localhost:8000/weather?city=Tokyo"
    ```
-   **Success Response** (`200 OK`):
    ```json
    {
      "city": "Tokyo",
      "temperature": 25.5,
      "description": "clear sky",
      "humidity": 60,
      "wind_speed": 3.5
    }
    ```

#### 2. Health Check
Verifies the operational status of the API.
-   **Endpoint**: `GET /health`
-   **Example**:
    ```bash
    curl -X GET "http://localhost:8000/health"
    ```
-   **Success Response** (`200 OK`):
    ```json
    {
      "status": "ok"
    }
    ```

#### 3. Usage Statistics
Provides simple usage statistics for the service.
-   **Endpoint**: `GET /stats`
-   **Example**:
    ```bash
    curl -X GET "http://localhost:8000/stats"
    ```
-   **Success Response** (`200 OK`):
    ```json
    {
      "total_requests": 50,
      "successful_requests": 48,
      "error_count": 2
    }
    ```

#### 4. Interactive API Documentation
This service provides interactive API documentation (Swagger UI) generated automatically by FastAPI.
-   **URL**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Development Environment

For development, use the `docker-compose.dev.yml` override file, which enables hot-reloading for the FastAPI application.

1.  **Start the development stack**:
    ```bash
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
    ```
    This command mounts the `app/` directory into the container. Any changes you make to the source code will trigger an automatic reload of the FastAPI server.

2.  **View Logs**:
    To see the logs from all running services:
    ```bash
    docker compose logs -f
    ```
    To view logs for a specific service (e.g., `weather-api`):
    ```bash
    docker compose logs -f weather-api
    ```

## Deployment

The provided `docker-compose.yml` file is designed for a production-like deployment.

-   **Start Services**:
    ```bash
    ./scripts/start.sh
    ```
-   **Stop Services**:
    The stop script ensures a clean shutdown, removing containers and anonymous volumes.
    ```bash
    ./scripts/stop.sh
    ```
-   **Restarting**:
    To restart the services, simply run `./scripts/stop.sh` followed by `./scripts/start.sh`.

## Testing

A comprehensive test suite is included using `pytest`. The tests cover API endpoints, service logic, and error handling.

-   **Run Tests**:
    The `test.sh` script executes the test suite against a running instance of the service. First, ensure the services are running with `./scripts/start.sh`.
    ```bash
    ./scripts/test.sh
    ```
    The script sends a test request to the API and reports the outcome. For more detailed tests, you can run `pytest` inside the container. When starting the project by
    ```bash
    docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
    ```
    you can run the tests by
    ```bash
    docker exec -it weather-api pytest tests/test_api.py -v
    ```

## Monitoring and Management

-   **Health and Stats**: Use the `/health` and `/stats` endpoints for basic monitoring.
-   **MinIO Console**: Access the MinIO web console at **[http://localhost:9001](http://localhost:9001)**. Use the default credentials (`minioadmin`/`minioadmin`) to log in and browse the `weather-data` bucket.
-   **DynamoDB Admin**: Access the DynamoDB Admin UI at **[http://localhost:8001](http://localhost:8001)** to view the `events` table and inspect logged data.
-   **Structured Logs**: The application uses structured logging (JSON format), which can be easily integrated with log management systems like Elasticsearch, Logstash, or Splunk.

## Troubleshooting

-   **`./scripts/start.sh` fails**:
    -   **Port Conflict**: Ensure ports `8000`, `8001`, `9000`, and `9001` are free. You can check with `lsof -i :<port>`.
    -   **Docker Daemon**: Make sure your Docker daemon is running.
-   **API returns `401 Unauthorized`**:
    -   Your `OPENWEATHERMAP_API_KEY` in `.env` is likely invalid or has not been activated yet. Please check your key and try again.
-   **API returns `500 Internal Server Error`**:
    -   Check the container logs with `docker compose logs -f weather-api` to diagnose the issue. It could be a problem connecting to MinIO or DynamoDB.
-   **MinIO or DynamoDB connection issues**:
    -   Ensure the `minio` and `dynamodb-local` containers are running and healthy. Check with `docker ps` and inspect their logs.

## Contributing

Contributions are welcome! Please follow these steps to contribute:

1.  **Fork** the repository.
2.  Create a new **feature branch** (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Ensure the tests pass (`./scripts/test.sh`).
5.  Commit your changes (`git commit -am 'Add new feature'`).
6.  **Push** to the branch (`git push origin feature/your-feature-name`).
7.  Create a new **Pull Request**.

---

[python-badge]: https://img.shields.io/badge/Python-3.11-3776AB.svg?style=flat-square
[python-link]: https://www.python.org/
[fastapi-badge]: https://img.shields.io/badge/FastAPI-0.104.0-009688.svg?style=flat-square
[fastapi-link]: https://fastapi.tiangolo.com/
[docker-badge]: https://img.shields.io/badge/Docker-24.0-2496ED.svg?style=flat-square
[docker-link]: https://www.docker.com/
[license-badge]: https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square
[license-link]: https://opensource.org/licenses/MIT
[black-badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[black-link]: https://github.com/psf/black
