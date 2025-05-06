# ElasticSearch / PopstgreSQL

This repo is a web application for generating, storing, and searching geospatial data about persons, leveraging **PostgreSQL** for persistent storage and **Elasticsearch** for fast geospatial and partial text searches. The application supports generating synthetic person data, synchronising data between PostgreSQL and Elasticsearch, and performing searches based on location (geospatial) or partial text matches.

## Features
- **Geospatial Search**: Find persons within a specified radius of a given latitude and longitude using Elasticsearch’s `geo_point` mapping.
- **Partial Text Search**: Perform partial matches on names and addresses with Elasticsearch’s `ngram` analyzer.
- **Data Generation**: Generate synthetic person data (e.g., name, address, coordinates) stored in PostgreSQL and indexed in Elasticsearch.
- **Bulk Synchronisation**: Efficiently sync modified or deleted records between PostgreSQL and Elasticsearch using the Elasticsearch Bulk API.
- **Web Interface**: A simple frontend for generating data and performing searches.
- **Scalable Architecture**: Combines PostgreSQL’s robust storage with Elasticsearch’s search performance.

## Architecture
The example uses a hybrid database approach:
- **PostgreSQL** (with PostGIS extension):
  - Stores person data (e.g., name, address, email, phone, coordinates) in a `personnes` table.
  - Uses a `GEOMETRY(POINT, 4326)` column (`geom`) for geospatial coordinates.
  - Tracks record modifications with a `last_modified` timestamp for synchronisation.
  - Ensures data integrity and persistence.
- **Elasticsearch**:
  - Indexes person data for fast search operations.
  - Maps the `geom` field as a `geo_point` for geospatial queries (e.g., finding persons within 1000m of a point).
  - Uses an `ngram` analyzer (`min_gram: 3`, `max_gram: 4`) for partial text search on `nom` and `adresse` fields.
  - Synchronises with PostgreSQL using a bulk API to handle large datasets efficiently.
- **Synchronisation**:
  - The `/sync` endpoint compares PostgreSQL and Elasticsearch records based on `last_modified` timestamps stored in `/app/last_sync.txt`.
  - Uses Elasticsearch’s Bulk API to index updated/new records and delete obsolete ones, avoiding timeouts for large datasets.
- **Web Frontend**:
  - Built with Nginx.
  - Provides forms for generating data and searching by location or text.

## Prerequisites
- **Docker** and **Docker Compose**: To run the application services.
- **Python 3.9+**: For local development (optional).


## Setup
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/voirinprof/gis_es_postgresql_docker.git
   cd gis_es_postgresql_docker
   ```

2. **Configure Environment**:
   Copy the example environment file and adjust if needed:
   ```bash
   cp .env.example .env
   ```
   Default settings in `.env`:
   - `POSTGRES_DB=geolab`
   - `POSTGRES_USER=geolab_user`
   - `POSTGRES_PASSWORD=geolab_pass`
   - `ELASTICSEARCH_HOST=http://elasticsearch:9200`

3. **Start Services**:
   Launch PostgreSQL, Elasticsearch, the Flask API, and the Jekyll frontend:
   ```bash
   docker-compose up -d
   ```

4. **Verify Setup**:
   - Check PostgreSQL: `docker-compose logs postgres`
   - Check Elasticsearch: `curl http://localhost:9200`
   - Check API: `curl http://localhost/api/health`
   - Access the web interface: `http://localhost`

## Usage
### Generate Data
Generate 100 synthetic person records:
```bash
curl -X POST -H "Content-Type: application/json" -d '{"count": 100}' http://localhost/api/generate
```
Or use the web interface at `http://localhost` to generate data.

### Synchronise Data
Sync PostgreSQL with Elasticsearch:
```bash
curl -X POST http://localhost/api/sync
```
This updates Elasticsearch with new/modified records and removes deleted ones, using the Bulk API for efficiency.

### Search
- **Geospatial Search** (find persons within 1000m of a point):
  ```bash
  curl http://localhost/api/search?lat=45.5&lon=-73.5&radius=1000
  ```
  Example response:
  ```json
  {
      "results": [
          {
              "firstname": "Marie",
              "lastname": "Dupont",
              "address": "123 Rue Principale",
              "city": "Sherbrooke",
              "location": {"lat": 45.401, "lon": -73.502},
              ...
          },
          ...
      ]
  }
  ```

- **Partial Text Search** (find persons by partial name/address):
  ```bash
  curl http://localhost/api/search?q=Dup
  ```
  Example response:
  ```json
  {
      "results": [
          {
              "firstname": "Jean",
              "lastname": "Dupont",
              ...
          },
          ...
      ]
  }
  ```

### Web Interface
- Open `http://localhost` in a browser.
- Use the forms to:
  - Generate data (specify count).
  - Search by location (latitude, longitude, radius).
  - Search by text (partial name or address).

## Project Structure
```
pythongeolab/
├── api/
│   ├── src/app.py          # Flask API (data generation, sync, search)
│   ├── mappings/persons.json  # Elasticsearch mapping (geo_point, ngram)
│   ├── Dockerfile          # API container configuration
│   ├── requirements.txt    # Python dependencies (elasticsearch, psycopg2, etc.)
├── db/
│   ├── postgres/init.sql   # PostgreSQL schema (personnes table with PostGIS)
├── web/                    # nginx / frontend
├── docker-compose.yml      # Defines services (postgres, elasticsearch, api, nginx)
```

## Contributing
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit changes: `git commit -m "Add feature"`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.

Please include tests in `api/tests/` for new features and update this README if necessary.

## Troubleshooting
- **Elasticsearch Index Issues**:
  - Verify mapping: `curl http://localhost:9200/persons/_mapping?pretty`
  - Recreate index: `docker-compose restart api`
- **Synchronisation Timeouts**:
  - The Bulk API handles large datasets. For very large datasets, consider batching (see `api/src/app.py`).
- **PostgreSQL Connection**:
  - Check logs: `docker-compose logs postgres`
  - Ensure `.env` matches `docker-compose.yml` credentials.
- **Web Interface**:
  - Rebuild Jekyll: `docker-compose restart nginx`

## License
MIT License. See `LICENSE` for details.