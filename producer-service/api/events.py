import json
import uuid
from datetime import datetime, timezone
import pika
import os
import logging

logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
EXCHANGE_NAME = 'product_events'
QUEUE_NAME = 'product_events_queue'
DLX_NAME = 'product_events_dlx'
DLQ_NAME = 'product_events_dlq'

def get_rabbitmq_connection():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        return connection
    except Exception as e:
        logger.error(f"Failed to connect to RabbitMQ: {e}")
        raise

def setup_rabbitmq():
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        
        # Setup Dead Letter Exchange and Queue
        channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct')
        channel.queue_declare(queue=DLQ_NAME)
        channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key='product_events_dlq')
        
        # Setup Main Exchange and Queue with DLX configuration
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
        channel.queue_declare(queue=QUEUE_NAME, arguments={
            'x-dead-letter-exchange': DLX_NAME,
            'x-dead-letter-routing-key': 'product_events_dlq'
        })
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key='product')
        
        connection.close()
    except Exception as e:
        logger.error(f"Error setting up RabbitMQ: {e}")

def publish_event(event_type, product_id, payload):
    connection = get_rabbitmq_connection()
    channel = connection.channel()
    
    event_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    message = {
        'event_id': event_id,
        'timestamp': timestamp,
        'event_type': event_type,
        'product_id': product_id,
        'payload': payload
    }
    
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key='product',
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # make message persistent
            content_type='application/json'
        )
    )
    
    connection.close()
    return event_id
