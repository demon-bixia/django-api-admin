from rest_framework import serializers
from test_django_api_admin.models import Author


class TestAuthorSerializer(serializers.ModelSerializer):
    """
    Serializer for the Author model.
    Serializes all the key fields and includes a URL for retrieving the detail view of the author.
    """
    class Meta:
        model = Author
        # Include id and all fields expected to be serialized.
        fields = [
            'id',
            'name',
            'age',
            'is_vip',
            'user',
            'publisher',
            'gender',
            'date_joined',
            'title',
            'url'
        ]
        read_only_fields = ['date_joined']
