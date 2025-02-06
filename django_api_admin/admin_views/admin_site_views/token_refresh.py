from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.views import APIView


class RefreshView(TokenRefreshView, APIView):
    permission_classes = []
    admin_site = None
