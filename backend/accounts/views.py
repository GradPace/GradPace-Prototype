from rest_framework.response import Response
from rest_framework.views import APIView


class MeView(APIView):
    """Protected - proves a simplejwt access token authenticates correctly."""

    def get(self, request):
        return Response(
            {
                "id": request.user.pk,
                "username": request.user.username,
                "email": request.user.email,
            }
        )
