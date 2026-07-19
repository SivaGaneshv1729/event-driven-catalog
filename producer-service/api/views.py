from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ProductEventSerializer
from .events import publish_event, setup_rabbitmq
import logging

logger = logging.getLogger(__name__)

class ProductEventView(APIView):
    def post(self, request):
        serializer = ProductEventSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Try setting up rabbitmq queues before publishing just in case
                setup_rabbitmq()
                
                event_id = publish_event(
                    event_type=serializer.validated_data['event_type'],
                    product_id=serializer.validated_data['product_id'],
                    payload=serializer.validated_data['payload']
                )
                return Response({
                    "status": "success",
                    "message": "Event published",
                    "event_id": event_id
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")
                return Response({
                    "status": "error",
                    "message": "Failed to publish event to message broker"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "healthy"}, status=status.HTTP_200_OK)
