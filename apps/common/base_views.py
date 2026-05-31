from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.views import APIView


class BaseAPIView(APIView):
    parser_classes = [JSONParser, FormParser, MultiPartParser]
