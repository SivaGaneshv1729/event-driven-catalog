import json
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

INDEX_FILE_PATH = os.path.join(settings.BASE_DIR, 'search_index.json')

def load_index():
    if os.path.exists(INDEX_FILE_PATH):
        try:
            with open(INDEX_FILE_PATH, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning("Search index file is corrupted, recreating.")
            return {}
    return {}

def save_index(index_data):
    with open(INDEX_FILE_PATH, 'w') as f:
        json.dump(index_data, f, indent=4)

def update_search_index(product_id, payload, event_type):
    index = load_index()
    
    if event_type == 'ProductCreated':
        index[product_id] = {
            'id': product_id,
            'name': payload.get('name', ''),
            'description': payload.get('description', ''),
            'price': str(payload.get('price', 0))
        }
    elif event_type == 'ProductUpdated':
        if product_id in index:
            for k, v in payload.items():
                if k in ['name', 'description', 'price']:
                    index[product_id][k] = str(v) if k == 'price' else v
    elif event_type == 'ProductDeleted':
        if product_id in index:
            del index[product_id]
            
    save_index(index)

def search_products(query):
    index = load_index()
    results = []
    
    query = query.lower()
    for prod_id, data in index.items():
        if query in data.get('name', '').lower() or query in data.get('description', '').lower():
            results.append(data)
            
    return results
