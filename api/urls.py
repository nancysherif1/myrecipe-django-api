# api/urls.py
from django.urls import path

from api.views import OrdersListAPIView

urlpatterns = [
    path('orders/', OrdersListAPIView.as_view(), name='order-list'),
]
