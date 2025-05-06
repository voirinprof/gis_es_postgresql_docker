from flask import Flask, jsonify, request
from elasticsearch import Elasticsearch, helpers
import psycopg2
import os
import json
from faker import Faker
import logging
from datetime import datetime, timezone
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
faker = Faker('fr_CA')

# settings for PostgreSQL connection
def connect_to_postgres(retries=5, delay=5):
    for attempt in range(retries):
        try:
            conn = psycopg2.connect(
                dbname=os.getenv('POSTGRES_DB', 'geolab'),
                user=os.getenv('POSTGRES_USER', 'geolab_user'),
                password=os.getenv('POSTGRES_PASSWORD', 'geolab_pass'),
                host=os.getenv('POSTGRES_HOST', 'postgres')
            )
            logging.info("Connexion à PostgreSQL réussie")
            return conn
        except psycopg2.OperationalError as e:
            logging.warning(f"Échec de la connexion à PostgreSQL (tentative {attempt + 1}/{retries}) : {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2  # Backoff exponentiel
            else:
                raise

pg_conn = connect_to_postgres()
pg_cursor = pg_conn.cursor()

# settings for Elasticsearch connection
es = Elasticsearch([os.getenv('ELASTICSEARCH_HOST', 'http://elasticsearch:9200')])

# Create index if it doesn't exist
try:
    with open('/app/mappings/persons.json') as f:
        mapping = json.load(f)
    # Supprimer l'index existant pour éviter les conflits
    es.options(ignore_status=[400, 404]).indices.delete(index='persons')
    # Créer l'index avec le mapping
    response = es.options(ignore_status=[400]).indices.create(index='persons', body=mapping)
    logging.info(f"Index 'personnes' créé avec succès : {response}")
except Exception as e:
    logging.error(f"Erreur lors de la création de l'index Elasticsearch : {e}")
    raise

# file for storing the last sync time
LAST_SYNC_FILE = '/app/last_sync.txt'

# get the last sync time from the file
def get_last_sync_time():
    try:
        with open(LAST_SYNC_FILE, 'r') as f:
            return datetime.fromisoformat(f.read().strip())
    except (FileNotFoundError, ValueError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)

# set the last sync time to the current time
def set_last_sync_time():
    with open(LAST_SYNC_FILE, 'w') as f:
        f.write(datetime.now(timezone.utc).isoformat())

# health check endpoint
@app.route('/health')
def health():
    try:
        es_info = es.info()
        return jsonify({'status': 'ok', 'elasticsearch': es_info})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# endpoint to generate random data
@app.route('/generate', methods=['POST'])
def generate_data():
    try:
        count = request.json.get('count', 100)
        for _ in range(count):
            firstname = faker.first_name()
            lastname = faker.last_name()
            prsaddress = faker.street_address()
            city = faker.city()
            postal_code = faker.postcode()
            country = 'Canada'
            email = faker.email()
            phone = faker.phone_number()
            # generate random coordinates around Montreal
            lat = float(faker.latitude()) % 0.1 + 45.4  # 45.4 à 45.5
            lon = float(faker.longitude()) % 0.1 - 73.6  # -73.6 à -73.5
            last_modified = datetime.now(timezone.utc)
            
            # Insert into PostgreSQL
            pg_cursor.execute("""
                INSERT INTO persons (firstname, lastname, prsaddress, city, postal_code, country, email, phone, geom, last_modified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s)
                RETURNING id
            """, (firstname, lastname, prsaddress, city, postal_code, country, email, phone, lon, lat, last_modified))
            person_id = pg_cursor.fetchone()[0]
            pg_conn.commit()
            
            # Index in Elasticsearch if you need to
            
            # doc = {
            #     'firstname': firstname,
            #     'lastname': lastname,
            #     'address': prsaddress,
            #     'city': city,
            #     'postal_code': postal_code,
            #     'country': country,
            #     'email': email,
            #     'phone': phone,
            #     'location': {'lat': lat, 'lon': lon},
            #     'last_modified': last_modified.isoformat()
            # }
            # Index the document in Elasticsearch
            # es.index(index='persons', id=person_id, body=doc)
        
        logging.info(f"{count} generated persons")
        return jsonify({'message': f'{count} generated persons'})
    except Exception as e:
        pg_conn.rollback()
        return jsonify({'error': str(e)}), 500

# endpoint to sync data between PostgreSQL and Elasticsearch
@app.route('/sync', methods=['POST'])
def sync_data():
    try:
        last_sync_time = get_last_sync_time()
        current_time = datetime.now(timezone.utc)
        
        # Get records modified since the last sync
        pg_cursor.execute("""
            SELECT id, firstname, lastname, prsaddress, city, postal_code, country, email, phone,
                   ST_X(geom) AS lon, ST_Y(geom) AS lat, last_modified
            FROM persons
            WHERE last_modified > %s
        """, (last_sync_time,))
        modified_records = pg_cursor.fetchall()
        
        # get ids from PostgreSQL
        pg_cursor.execute("SELECT id FROM persons")
        pg_ids = set(row[0] for row in pg_cursor.fetchall())
        
        # get ids from Elasticsearch
        es_ids = set()
        res = es.search(index='persons', body={'query': {'match_all': {}}}, size=10000)
        for hit in res['hits']['hits']:
            es_ids.add(int(hit['_id']))
        
        # find ids to delete
        ids_to_delete = es_ids - pg_ids
        
        # prepare bulk actions
        bulk_actions = []
        
        # add modified records to bulk actions
        for record in modified_records:
            person_id, firstname, lastname, prsaddress, city, postal_code, country, email, phone, lon, lat, last_modified = record
            doc = {
                'firstname': firstname,
                'lastname': lastname,
                'address': prsaddress,
                'city': city,
                'postal_code': postal_code,
                'country': country,
                'email': email,
                'phone': phone,
                'location': {'lat': lat, 'lon': lon},
                'last_modified': last_modified.isoformat()
            }
            bulk_actions.append({
                '_op_type': 'index',
                '_index': 'persons',
                '_id': person_id,
                '_source': doc
            })
            logging.debug(f"Preparing indexation of {person_id} with location: {doc['location']}")
        
        # Ajouter les opérations de suppression
        for id_to_delete in ids_to_delete:
            bulk_actions.append({
                '_op_type': 'delete',
                '_index': 'persons',
                '_id': id_to_delete
            })
            logging.debug(f"Preparing deletion of person {id_to_delete}")
        
        # Exécuter les opérations bulk
        if bulk_actions:
            success, failed = helpers.bulk(es, bulk_actions, raise_on_error=False)
            logging.info(f"Bulk sync completed: {success} succeeded, {failed} failed")
            if failed:
                logging.error(f"Errors in bulk operations: {failed}")
        else:
            logging.info("No bulk operations to execute")
        
        # Update the last sync time
        set_last_sync_time()
        
        logging.info(f"Synchronization completed: {len(modified_records)} updated/inserted, {len(ids_to_delete)} deleted")
        return jsonify({
            'message': 'Synchronization completed',
            'updated_inserted': len(modified_records),
            'deleted': len(ids_to_delete),
            'bulk_success': success if bulk_actions else 0,
            'bulk_failed': failed if bulk_actions else 0
        })
    except Exception as e:
        logging.error(f"Error during sync: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius = request.args.get('radius', default=1000, type=int)
    
    try:
        if query:
            # Use wildcard search for Elasticsearch
            query = f"*{query.lower()}*"
            body = {
                'query': {
                    'query_string': {
                        'query': query,
                        'fields': ['lastname', 'address'],
                        'default_operator': 'AND'
                    }
                }
            }
        # if lat and lon are provided, use geo_distance
        elif lat and lon:
            body = {
                'query': {
                    'geo_distance': {
                        'distance': f'{radius}m',
                        'location': {'lat': lat, 'lon': lon}
                    }
                }
            }
        else:
            return jsonify({'error': 'Parameters q or lat/lon required'}), 400
        
        res = es.search(index='persons', body=body, size=20)
        results = [hit['_source'] for hit in res['hits']['hits']]
        return jsonify({'results': results})
    except Exception as e:
        logging.error(f"Error during search: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)