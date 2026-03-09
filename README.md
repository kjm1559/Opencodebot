# Stock News API

A FastAPI-based stock news aggregation system that collects news from multiple sources (Finnhub, AlphaVantage, GNews) with scheduled data collection via Celery.

## Features

- **Multi-source news aggregation**: Finnhub (primary), AlphaVantage, GNews (stubs)
- **Scheduled collection**: Runs every 5 minutes via Celery Beat
- **Deduplication**: SHA-256 hash-based article deduplication
- **Async database**: PostgreSQL with async SQLAlchemy 2.0
- **RESTful API**: FastAPI endpoints for news retrieval
- **Containerized**: Docker Compose for PostgreSQL and Redis

## Quick Start

```bash
# Start infrastructure
docker compose up -d

# Initialize database
alembic upgrade head

# Seed company data
seed-db

# Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A app.celery worker -l info -Q news_collection,maintenance

# Start Celery Beat (separate terminal)
celery -A app.celery beat -l info
```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Environment Setup

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
# Required
FINNHUB_API_KEY=your_finnhub_key_here

# Optional
ALPHAVANTAGE_API_KEY=
GNEWS_API_KEY=
```

## API Endpoints

### Articles
- `GET /api/v1/articles` - List articles with pagination and filters
  - Query params: `page`, `page_size`, `ticker`, `source`
- `GET /api/v1/articles/{id}` - Get single article by ID
- `POST /api/v1/news/collect` - Manually trigger news collection

### Companies  
- `GET /api/v1/companies` - List all companies with article counts

### Health
- `GET /api/v1/health` - Health check endpoint

## Project Structure

```
stock_info/
├── app/
│   ├── api/           # FastAPI routes
│   │   ├── routes.py  # Endpoints
│   │   └── schemas.py # Pydantic models
│   ├── collectors/    # News API collectors
│   │   ├── finnhub.py # Finnhub collector
│   │   ├── alphavantage.py  # AlphaVantage stub
│   │   └── gnews.py   # GNews stub
│   ├── celery.py      # Celery configuration
│   ├── config.py      # Settings
│   ├── database.py    # Async DB session
│   ├── main.py        # FastAPI app
│   ├── models.py      # SQLAlchemy models
│   └── tasks.py       # Celery tasks
├── alembic/           # Database migrations
├── scripts/           # Utility scripts
│   └── seed_companies.py
├── tests/             # Pytest test suite
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## Database Schema

**Tables:**
- `companies`: Stock ticker information (ticker, name, sector)
- `articles`: News content with deduplication
- `article_companies`: Many-to-many association
- `article_signals`: Sentiment/relevance scores

**Deduplication:**
Articles are deduplicated using SHA-256 hash of `(title + url)` stored in `content_hash` column.

## Celery Tasks

### Scheduled Tasks (via Celery Beat)
- `collect_news_for_all_companies`: Runs every 5 minutes
  - Fetches news from last 24 hours per company
  - Deduplicates before insertion  
  - Rate-limited to avoid API throttling

- `cleanup_old_articles`: Runs daily at 3 AM
  - Deletes articles older than 90 days
  - Retries on failure (max 3 attempts)

### Manual Tasks
- `collect_news_on_startup`: One-time initial collection

## News Collection Flow

1. Celery Beat triggers `collect_news_for_all_companies` every 5 minutes
2. Task fetches news from Finnhub API for each active company  
3. Articles are deduplicated by hash before insertion
4. Only last 24 hours of news (to avoid rate limits)
5. Old articles (90+ days) are automatically cleaned up daily

## Tests

```bash
# Run all tests
pytest -v --cov=app

# Run specific test suite
pytest tests/unit/ -v           # Unit tests
pytest tests/integration/ -v    # Integration tests
pytest tests/e2e/ -v           # End-to-end tests
```

### Test Coverage

- **Unit Tests**: Model validation, hash computation
- **Integration Tests**: API endpoints, database operations
- **E2E Tests**: Full workflows with seeded data

## Configuration

### Database
- PostgreSQL 15 with asyncpg driver
- Connection pooling configured
- Alembic migrations for schema management

### Celery  
- Redis as message broker
- JSON serialization
- Two queues: `news_collection`, `maintenance`
- Rate limiting: 1 task per minute

### API
- FastAPI with automatic OpenAPI docs
- CORS enabled for all origins
- Async database sessions per request

## Development

### Adding New News Source

1. Create collector in `app/collectors/`
2. Implement `get_company_news()` method
3. Update Celery task to use new collector
4. Add API key to `.env`

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Troubleshooting

### Database Connection Errors
- Verify PostgreSQL is running in Docker
- Check `.env` database credentials
- Run `docker compose logs db` for logs

### Celery Worker Not Starting  
- Verify Redis is running: `docker compose logs redis`
- Check `celery_broker_url` in `.env`
- Ensure Celery worker queue names match config

### API Rate Limits
- Finnhub free tier: 60 calls/minute
- Task is rate-limited to avoid exceeding limits
- Increase delay in `tasks.py` if needed

## License

MIT License
