from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch

class ProductEventTests(APITestCase):

    @patch('api.views.setup_rabbitmq')
    @patch('api.views.publish_event')
    def test_create_product_event_success(self, mock_publish, mock_setup):
        mock_publish.return_value = 'test-event-id-123'
        
        payload = {
            "event_type": "ProductCreated",
            "product_id": "prod_123",
            "payload": {
                "name": "Test Product",
                "description": "Test Desc",
                "price": 99.99,
                "stock": 10
            }
        }
        
        response = self.client.post('/api/products/events', payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['event_id'], 'test-event-id-123')
        
        mock_publish.assert_called_once_with(
            event_type="ProductCreated",
            product_id="prod_123",
            payload=payload['payload']
        )

    def test_create_product_event_missing_fields(self):
        payload = {
            "event_type": "ProductCreated",
            "product_id": "prod_123",
            "payload": {
                "name": "Test Product",
                # missing description, price, stock
            }
        }
        
        response = self.client.post('/api/products/events', payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
