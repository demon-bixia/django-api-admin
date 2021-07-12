from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _

UserModel = get_user_model()


class InvalidUsage(Exception):
    pass


class LoginSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True,
                                     style={'input_type': 'password', 'placeholder': 'Password'})

    auth_error_messages = {
        'invalid_login': _(
            "Please enter the correct %(username)s and password for a staff account. Note that both fields may be case-sensitive. "
        ) % {'username': UserModel.USERNAME_FIELD},

        'permission_denied': _("Please login with an account that has permissions to access the admin site"),

        'inactive': _("This account is inactive."),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None

        # create the username field
        username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
        self.username = serializers.ModelSerializer.serializer_field_mapping[username_field.__class__](required=True)
        self._declared_fields[UserModel.USERNAME_FIELD] = self.username

    def validate(self, data):
        username = data.get(UserModel.USERNAME_FIELD)
        password = data.get('password')
        request = self.context.get('request')

        if username is not None and password:
            self.user_cache = authenticate(request, username=username, password=password)
            if self.user_cache is None:
                raise serializers.ValidationError(self.auth_error_messages['invalid_login'], code='invalid_login')
            elif not self.user_cache.is_staff:
                raise serializers.ValidationError(self.auth_error_messages['permission_denied'],
                                                  code='permission_denied')
            elif not self.user_cache.is_active:
                raise serializers.ValidationError(self.auth_error_messages['inactive'], code='inactive')
        return data

    def get_user(self):
        return self.user_cache

    def create(self, validated_data):
        raise InvalidUsage("LoginSerializer doesn't allow usage of the create method.")

    def update(self, instance, validated_data):
        raise InvalidUsage("LoginSerializer doesn't allow usage of the update method.")

    def save(self, **kwargs):
        raise InvalidUsage("LoginSerializer doesn't allow usage of the save method")


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}
