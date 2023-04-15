""" 
views used to test the not included for production.
"""
import datetime
import json

from django.conf import settings

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_admin.models import Author
from django_api_admin.declarations.functions import get_form_fields

tests = {
    # char field tests
    'char_field_render_test': [
        {
            "username": serializers.CharField(max_length=30, min_length=3, help_text="enter your name here"),
        }
    ],

    'char_field_null_test': [
        {
            "username": serializers.CharField(max_length=30, min_length=3, allow_blank=True, allow_null=True),
        }
    ],

    'char_field_default_test': [
        {
            "username": serializers.CharField(max_length=30, min_length=3, default="hello world", initial="somthing else"),
        }
    ],

    'textarea_field_test': [
        {
            "bio": serializers.CharField(max_length=30, min_length=3, help_text="information about yourself", style={'input_type': 'textarea'}),
        }
    ],

    'email_field_test': [
        {
            'email': serializers.EmailField(max_length=255, min_length=12, allow_blank=True)
        }
    ],

    'regex_field_test': [
        {
            'regex': serializers.RegexField(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', max_length=255, min_length=2, allow_blank=False)
        }
    ],

    'slug_field_test': [
        {
            'slug': serializers.SlugField(max_length=50, min_length=3, allow_blank=True)
        }
    ],

    'url_field_test': [
        {
            'url': serializers.URLField(max_length=200, min_length=3, allow_blank=False)
        }
    ],

    'uuid_field_test': [
        {
            'uuid': serializers.UUIDField(format='hex_verbose', allow_null=True)
        }
    ],

    'ip_address_filed_test': [
        {
            'ip_address': serializers.IPAddressField(protocol='both', max_length=200, min_length=3, allow_blank=False)
        }
    ],

    'integer_field_test': [
        {
            'int': serializers.IntegerField(max_value=10, min_value=0, allow_null=True)
        }
    ],

    'float_field_test': [
        {
            'float': serializers.FloatField(max_value=10, min_value=1)
        }
    ],

    'decimal_field_test': [
        {
            'decimal': serializers.DecimalField(max_digits=5, decimal_places=2, max_value=1000, min_value=1)
        }
    ],

    'json_field_test': [
        {
            'json': serializers.JSONField(default=json.dumps({"username": "admin"})),
        }
    ],

    # password field tests
    'password_field_test': [
        {
            'password': serializers.CharField(min_length=6, max_length=80, allow_blank=False, required=True, style={'input_type': 'password'})
        }
    ],

    # choice fields tests
    'choice_field_test': [
        {
            'choice': serializers.ChoiceField(choices=[('1', 'admin'), ('2', 'worker')], initial='1')
        }
    ],


    'choice_field_null_test': [
        {
            'choice': serializers.ChoiceField(choices=[('1', 'admin'), ('2', 'worker')], allow_null=True)
        }
    ],

    'choice_field_default_test': [
        {
            'choice': serializers.ChoiceField(choices=[('1', 'admin'), ('2', 'worker')], default='1')
        }
    ],

    'multi_choice_field_test': [
        {
            'multi_choice': serializers.MultipleChoiceField(choices=[('1', 'admin'), ('2', 'worker')])
        }
    ],

    'file_path_field_test': [
        {
            'file': serializers.FilePathField(path=settings.BASE_DIR / 'api_admin')
        }
    ],

    # boolean field tests
    'boolean_field_test': [
        {
            'is_vip': serializers.BooleanField()
        }
    ],

    'boolean_field_default_test': [
        {
            'is_vip': serializers.BooleanField(default=True)
        }
    ],

    # date field tests
    'date_field_test': [
        {
            'date': serializers.DateField()
        }
    ],

    'date_field_null_test': [
        {
            'date': serializers.DateField(allow_null=True)
        }
    ],

    'date_field_default_test': [
        {
            'date': serializers.DateField(default=datetime.date.today())
        }
    ],

    'date_field_input_format_test': [
        {
            'date': serializers.DateField(input_formats=['%m/%d/%Y'])
        }
    ],

    # datetime field test
    'datetime_field_test': [
        {
            'datetime': serializers.DateTimeField()
        }
    ],

    'datetime_field_input_format_test': [
        {
            'datetime': serializers.DateTimeField(input_formats=['%Y-%m-%d %H:%M'])
        }
    ],

    'datetime_field_null_test': [
        {
            'datetime': serializers.DateTimeField(allow_null=True)
        }
    ],

    'datetime_field_default_test': [
        {
            'datetime': serializers.DateTimeField(default=datetime.datetime.now())
        }
    ],

    # time field test
    'time_field_test': [
        {
            'time': serializers.TimeField()
        }
    ],

    'time_field_default_test': [
        {
            'time': serializers.TimeField(default=datetime.datetime.now().time())
        }
    ],

    'time_field_null_test': [
        {
            'time': serializers.TimeField(allow_null=True)
        }
    ],

    'time_field_input_formats_test': [
        {
            'time': serializers.TimeField(input_formats=['%H:%M'])
        }
    ],

    # duration field test
    'duration_field_test': [
        {
            'duration': serializers.DurationField()
        }
    ],

    'duration_field_null_test': [
        {
            'duration': serializers.DurationField(allow_null=True)
        }
    ],

    'duration_field_default_test': [
        {
            'duration': serializers.DurationField(default=datetime.datetime.now())
        }
    ],

    # file field test
    'file_field_test': [
        {
            'file': serializers.FileField()
        }
    ],

    'file_field_null_test': [
        {
            'file': serializers.FileField(allow_null=True)
        }
    ],

    'file_field_default_test': [
        {
            'file': serializers.FileField(default='settings.BASE_DIR/manage.py')
        }
    ],

    'image_field_test': [
        {
            'image': serializers.ImageField()
        }
    ],

    # list field test
    'list_field_no_child_test': [
        {
            'scores': serializers.ListField()
        }
    ],

    'list_field_test': [
        {
            'scores': serializers.ListField(child=serializers.IntegerField(label="score"), min_length=1, max_length=2)
        }
    ],

    'list_field_default_test': [
        {
            'scores': serializers.ListField(default=[1, 2, 3], child=serializers.IntegerField(label="score"))
        }
    ],

    'list_field_null_test': [
        {
            'scores': serializers.ListField(allow_null=True, child=serializers.IntegerField(label="score", allow_null=True))
        }
    ],

    # dict field test
    'dict_field_no_child_test': [
        {
            'config': serializers.DictField()
        }
    ],

    'dict_field_test': [
        {
            'config': serializers.DictField(child=serializers.CharField(label="value"))
        },
    ],

    'dict_field_null_test': [
        {
            'config': serializers.DictField(allow_null=True, child=serializers.CharField(label="value", allow_null=True))
        }
    ],

    'dict_field_default_test': [
        {
            'config': serializers.DictField(default={'username': 'admin'}, child=serializers.CharField(label="value"))
        }
    ],

    'hstore_field_test': [
        {
            'enviornment_variables': serializers.HStoreField(initial={"admin": "password", "save": True})
        }
    ],

    # PrimaryKeyRelatedField tests
    'primary_key_related_field_test': [
        {
            'authors': serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), pk_field=serializers.FloatField())
        }
    ],

    'primary_key_related_field_many_test': [
        {
            'authors': serializers.PrimaryKeyRelatedField(queryset=Author.objects.all(), many=True)
        }
    ],

    'hyperlinked_related_field_test': [
        {
            'authors': serializers.HyperlinkedRelatedField(queryset=Author.objects.all(), view_name='test-detail')
        },

        serializers.ModelSerializer,

        {'model': Author, 'fields': ['authors']},
    ],

    'hyperlinked_related_field_many_test': [
        {
            'authors': serializers.HyperlinkedRelatedField(queryset=Author.objects.all(), view_name='test-detail', many=True)
        },

        serializers.ModelSerializer,

        {'model': Author, 'fields': ['authors']},
    ],

    'slug_related_field_test': [
        {
            'authors': serializers.SlugRelatedField(queryset=Author.objects.all(), slug_field='name')
        },

        serializers.ModelSerializer,

        {'model': Author, 'fields': ['authors']},
    ],

    'slug_related_field_many_test': [
        {
            'authors': serializers.SlugRelatedField(queryset=Author.objects.all(), slug_field='name', many=True)
        },

        serializers.ModelSerializer,

        {'model': Author, 'fields': ['authors']},
    ],
}


class TestView(APIView):
    """
    A view used for integrated tests.
    """
    authentication_classes = []
    serializer_class = None

    def get(self, request, test_name):
        try:
            fields, SerializerClass, meta = self.get_test(test_name)
            self.serializer_class = self.generate_test_serializer(
                SerializerClass, meta, fields)

            serializer = self.serializer_class(context={'request': request})
            form_fields = get_form_fields(serializer,)
        except KeyError:
            return Response({'detail': 'test field not supported'})

        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    def post(self, request, test_name):
        print(request.data)
        try:
            fields, SerializerClass, meta = self.get_test(test_name)
            serializer_class = self.generate_test_serializer(
                SerializerClass, meta, fields)
            serializer = serializer_class(data=request.data)

            if serializer.is_valid():
                return Response({"hello": "world"})
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except KeyError:
            return Response({'detail': 'test field not supported'})

    def generate_test_serializer(self, SerializerClass, meta, fields):
        return type('TestSerializer', (SerializerClass,), {**fields, 'Meta': type('Meta', (object,), {**meta})})

    def get_test(self, test_name):
        test = tests[test_name]
        fields = {}
        SerializerClass = serializers.Serializer
        meta = {}

        try:
            fields = test[0]
        except IndexError:
            pass

        try:
            SerializerClass = test[1]
        except IndexError:
            pass

        try:
            meta = test[2]
        except IndexError:
            pass

        return fields, SerializerClass, meta


class TestDetailView(APIView):
    def get(request, pk, format=None):
        return Response({}, status=status.HTTP_200_OK)
