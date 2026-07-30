import json
import pika
import os
import logging
import time
from django.core.management.base import BaseCommand
from django.db import transaction
from api.models import Product, ProcessedEvent
from api.services import update_search_index

logger = logging.getLogger(__name__)

RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
EXCHANGE_NAME = 'product_events'
QUEUE_NAME = 'product_events_queue'
DLX_NAME = 'product_events_dlx'
DLQ_NAME = 'product_events_dlq'
MAX_RETRIES = 3

class Command(BaseCommand):
    help = 'Consumes product events from RabbitMQ'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting RabbitMQ consumer..."))
        
        # Connect to RabbitMQ
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=RABBITMQ_HOST,
            heartbeat=600,
            blocked_connection_timeout=300
        ))
        channel = connection.channel()

        # Ensure DLX and DLQ exist
        channel.exchange_declare(exchange=DLX_NAME, exchange_type='direct')
        channel.queue_declare(queue=DLQ_NAME)
        channel.queue_bind(exchange=DLX_NAME, queue=DLQ_NAME, routing_key='product_events_dlq')
        
        # Ensure main exchange and queue exist, configure DLX
        channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct')
        channel.queue_declare(queue=QUEUE_NAME, arguments={
            'x-dead-letter-exchange': DLX_NAME,
            'x-dead-letter-routing-key': 'product_events_dlq'
        })
        channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key='product')

        # Set prefetch count to 1 for fair dispatch
        channel.basic_qos(prefetch_count=1)
        
        # Register the consumer
        channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=self.process_message,
        )

        try:
            channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
        connection.close()

    def process_message(self, ch, method, properties, body):
        for attempt in range(MAX_RETRIES):
            try:
                self.process_event(ch, method, properties, body)
                return  # Successfully processed or rejected natively
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed with error: {e}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)
                else:
                    logger.error("Max retries reached. Sending message to DLQ.")
                    ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)

    def process_event(self, ch, method, properties, body):
        try:
            event_data = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"Malformed JSON payload: {e}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        event_id = event_data.get('event_id')
        event_type = event_data.get('event_type')
        product_id = event_data.get('product_id')
        payload = event_data.get('payload')

        if not event_id or not event_type or not product_id or payload is None:
            logger.error("Invalid event format: missing event_id, event_type, product_id, or payload")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        # Check Idempotency
        if ProcessedEvent.objects.filter(event_id=event_id).exists():
            logger.info(f"Event {event_id} already processed. Ensuring search index is synced.")
            update_search_index(product_id, payload, event_type)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # DB transaction (outside of search index update)
        with transaction.atomic():
            if event_type == 'ProductCreated':
                Product.objects.create(
                    id=product_id,
                    name=payload.get('name', ''),
                    description=payload.get('description', ''),
                    price=payload.get('price', 0),
                    stock=payload.get('stock', 0),
                    status='active'
                )
            elif event_type == 'ProductUpdated':
                try:
                    product = Product.objects.select_for_update().get(id=product_id)
                    # Update only provided fields
                    for key, value in payload.items():
                        if hasattr(product, key):
                            setattr(product, key, value)
                    product.save()
                except Product.DoesNotExist:
                    logger.error(f"Product {product_id} not found for update.")
                    ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                    return
            elif event_type == 'ProductDeleted':
                try:
                    product = Product.objects.select_for_update().get(id=product_id)
                    product.status = 'deleted'
                    product.save()
                except Product.DoesNotExist:
                    logger.error(f"Product {product_id} not found for deletion.")
                    ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                    return
            else:
                logger.warning(f"Unknown event type: {event_type}")
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Record Processed Event
            ProcessedEvent.objects.create(event_id=event_id)

        # Update Search Index AFTER successful DB transaction commit
        try:
            update_search_index(product_id, payload, event_type)
        except Exception as index_err:
            logger.error(f"Failed to update search index: {index_err}")
            raise

        logger.info(f"Successfully processed event {event_id}")
        ch.basic_ack(delivery_tag=method.delivery_tag)
