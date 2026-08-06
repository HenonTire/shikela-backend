from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import get_supplier_dashboard_data


class ShopSupplierDirectoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role != "SHOP_OWNER":
            raise PermissionDenied("Only shop owners can view the supplier directory.")
        shop = getattr(user, "owned_shop", None)
        if not shop:
            raise PermissionDenied("Create a shop before viewing suppliers.")
        return Response(get_supplier_dashboard_data(shop))