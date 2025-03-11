from rest_framework.generics import ListAPIView
from api.models import Order
from api.serializers import OrderSerializer

class OrdersListAPIView(ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
