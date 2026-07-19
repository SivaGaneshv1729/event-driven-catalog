from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import search_products

class SearchProductsView(APIView):
    def get(self, request):
        query = request.query_params.get('q', '')
        results = search_products(query)
        return Response(results, status=status.HTTP_200_OK)

class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "healthy"}, status=status.HTTP_200_OK)
