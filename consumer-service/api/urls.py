from django.urls import path
from .views import SearchProductsView, HealthCheckView

urlpatterns = [
    path('products/search', SearchProductsView.as_view(), name='product-search'),
    path('products/search/', SearchProductsView.as_view(), name='product-search-slash'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('health', HealthCheckView.as_view(), name='health-check-no-slash'),
]
