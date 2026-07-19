from django.urls import path
from .views import ProductEventView, HealthCheckView

urlpatterns = [
    path('products/events', ProductEventView.as_view(), name='product-events'),
    path('health/', HealthCheckView.as_view(), name='health-check'),
]
