import json
from decimal import Decimal
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from api.models import Product, ProcessedEvent
from api.services import search_products, load_index, save_index
from api.management.commands.consume_events import Command

class ConsumerTests(APITestCase):
    
    def setUp(self):
        # Clear search index before tests
        save_index({})
        # Clear database
        Product.objects.all().delete()
        ProcessedEvent.objects.all().delete()

    def tearDown(self):
        # Clear search index after tests
        save_index({})

    def test_search_endpoint_returns_results(self):
        # Setup mock search index
        save_index({
            "prod_1": {"id": "prod_1", "name": "Wireless Earbuds", "description": "High quality sound", "price": "99.99"}
        })
        
        # Verify both trailing-slash and non-trailing-slash urls work
        for path in ['/api/products/search?q=earbuds', '/api/products/search/?q=earbuds']:
            response = self.client.get(path)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]['name'], 'Wireless Earbuds')

    def test_search_endpoint_empty_results(self):
        save_index({
            "prod_1": {"id": "prod_1", "name": "Wireless Earbuds", "description": "High quality sound", "price": "99.99"}
        })
        
        response = self.client.get('/api/products/search?q=nonexistent')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_process_product_created_success(self):
        cmd = Command()
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 1
        
        event_body = json.dumps({
            "event_id": "evt_create_101",
            "event_type": "ProductCreated",
            "product_id": "prod_101",
            "payload": {
                "name": "Mechanical Keyboard",
                "description": "RGB backlight keyboard",
                "price": 79.99,
                "stock": 50
            }
        })
        
        cmd.process_message(mock_ch, mock_method, None, event_body)
        
        # 1. DB verification
        self.assertTrue(Product.objects.filter(id="prod_101").exists())
        prod = Product.objects.get(id="prod_101")
        self.assertEqual(prod.name, "Mechanical Keyboard")
        self.assertEqual(prod.status, "active")
        
        # 2. Search Index verification
        index = load_index()
        self.assertIn("prod_101", index)
        self.assertEqual(index["prod_101"]["name"], "Mechanical Keyboard")
        
        # 3. Idempotency table verification
        self.assertTrue(ProcessedEvent.objects.filter(event_id="evt_create_101").exists())
        
        # 4. RabbitMQ acknowledgment verification
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=1)
        mock_ch.basic_reject.assert_not_called()

    def test_process_product_updated_success(self):
        # Pre-populate DB and index
        Product.objects.create(
            id="prod_102",
            name="Gaming Mouse",
            description="High precision wireless mouse",
            price=49.99,
            stock=30,
            status="active"
        )
        save_index({
            "prod_102": {"id": "prod_102", "name": "Gaming Mouse", "description": "High precision wireless mouse", "price": "49.99"}
        })
        
        cmd = Command()
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 2
        
        # Update only price and stock
        event_body = json.dumps({
            "event_id": "evt_update_102",
            "event_type": "ProductUpdated",
            "product_id": "prod_102",
            "payload": {
                "price": 39.99,
                "stock": 25
            }
        })
        
        cmd.process_message(mock_ch, mock_method, None, event_body)
        
        # DB verification (name should remain unchanged)
        prod = Product.objects.get(id="prod_102")
        self.assertEqual(prod.name, "Gaming Mouse")
        self.assertEqual(prod.price, Decimal('39.99'))
        self.assertEqual(prod.stock, 25)
        
        # Search index verification
        index = load_index()
        self.assertEqual(index["prod_102"]["name"], "Gaming Mouse")
        self.assertEqual(index["prod_102"]["price"], "39.99")
        
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=2)

    def test_process_product_deleted_success(self):
        # Pre-populate DB and index
        Product.objects.create(
            id="prod_103",
            name="Laptop Stand",
            description="Aluminum ergonomic stand",
            price=29.99,
            stock=15,
            status="active"
        )
        save_index({
            "prod_103": {"id": "prod_103", "name": "Laptop Stand", "description": "Aluminum ergonomic stand", "price": "29.99"}
        })
        
        cmd = Command()
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 3
        
        event_body = json.dumps({
            "event_id": "evt_delete_103",
            "event_type": "ProductDeleted",
            "product_id": "prod_103",
            "payload": {}
        })
        
        cmd.process_message(mock_ch, mock_method, None, event_body)
        
        # DB verification: Logical deletion (status must be 'deleted' and not hard deleted)
        self.assertTrue(Product.objects.filter(id="prod_103").exists())
        prod = Product.objects.get(id="prod_103")
        self.assertEqual(prod.status, "deleted")
        
        # Search index verification: Product must be removed/filtered out
        index = load_index()
        self.assertNotIn("prod_103", index)
        
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=3)

    def test_idempotent_event_processing(self):
        cmd = Command()
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 4
        
        event_body = json.dumps({
            "event_id": "evt_idemp_104",
            "event_type": "ProductCreated",
            "product_id": "prod_104",
            "payload": {
                "name": "USB Hub",
                "description": "4-port USB 3.0 hub",
                "price": 15.00,
                "stock": 100
            }
        })
        
        # Process once
        cmd.process_message(mock_ch, mock_method, None, event_body)
        self.assertEqual(Product.objects.filter(id="prod_104").count(), 1)
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=4)
        
        # Process identical event again
        mock_ch.reset_mock()
        cmd.process_message(mock_ch, mock_method, None, event_body)
        
        # Verify no duplicate db insertion
        self.assertEqual(Product.objects.filter(id="prod_104").count(), 1)
        # Verify acked successfully on subsequent delivery
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=4)
        mock_ch.basic_reject.assert_not_called()

    @patch('api.management.commands.consume_events.update_search_index')
    @patch('time.sleep')
    def test_dlq_routing_on_max_retries(self, mock_sleep, mock_update):
        # Force a write error during index synchronization to trigger retry
        mock_update.side_effect = Exception("Disk partition full / permission error")
        
        cmd = Command()
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 5
        
        event_body = json.dumps({
            "event_id": "evt_fail_105",
            "event_type": "ProductCreated",
            "product_id": "prod_105",
            "payload": {
                "name": "HDMI Cable",
                "description": "4K HDMI cable 6ft",
                "price": 9.99,
                "stock": 200
            }
        })
        
        cmd.process_message(mock_ch, mock_method, None, event_body)
        
        # Verify search index was attempted 3 times (MAX_RETRIES)
        self.assertEqual(mock_update.call_count, 3)
        # Verify it was rejected with requeue=False (sends to RabbitMQ DLQ)
        mock_ch.basic_reject.assert_called_once_with(delivery_tag=5, requeue=False)
        mock_ch.basic_ack.assert_not_called()

    def test_malformed_json_rejected_immediately(self):
        cmd = Command()
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 6
        
        # Non-JSON payload
        malformed_body = "not a valid json string"
        
        cmd.process_message(mock_ch, mock_method, None, malformed_body)
        
        # Malformed payloads should be rejected immediately without retrying
        mock_ch.basic_reject.assert_called_once_with(delivery_tag=6, requeue=False)
        mock_ch.basic_ack.assert_not_called()
