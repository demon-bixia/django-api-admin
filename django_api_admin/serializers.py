from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        exclude = ('password',)


class LoginSerializer(serializers.Serializer):
    """
    Validates login credentials and generates token.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_cache = None
        # create the username field
        username_field = UserModel._meta.get_field(UserModel.USERNAME_FIELD)
        self.username = serializers.ModelSerializer.serializer_field_mapping[username_field.__class__](
            max_length=username_field.max_length, required=True)
        self._declared_fields[UserModel.USERNAME_FIELD] = self.username
        self.password = serializers.CharField(label='Password', write_only=True, required=True,
                                              style={'input_type': 'password'}, max_length=80, min_length=7)
        self._declared_fields['password'] = self.password

        # add the custom error messages to self.error_messages
        self.error_messages.update({
            'invalid_login': _(
                "Please enter the correct %(username)s and password for a staff account."
                " Note that both fields may be case-sensitive. "
            ) % {'username': UserModel.USERNAME_FIELD},

            'permission_denied': _("Please login with an account that has permissions to access the admin site"),

            'inactive': _("This account is inactive."),
        })

    def validate(self, data):
        username = data.get(UserModel.USERNAME_FIELD)
        password = data.get('password')
        request = self.context.get('request')

        if username is not None and password:
            self.user_cache = authenticate(
                request, username=username, password=password)
            if self.user_cache is None:
                raise serializers.ValidationError(
                    self.error_messages['invalid_login'], code='invalid_login')
            elif not self.user_cache.is_staff:
                raise serializers.ValidationError(self.error_messages['permission_denied'],
                                                  code='permission_denied')
            elif not self.user_cache.is_active:
                raise serializers.ValidationError(
                    self.error_messages['inactive'], code='inactive')
        return data

    def get_user(self):
        if not hasattr(self, '_validated_data'):
            raise AssertionError(
                'You must call is valid before calling get_user')
        return self.user_cache


class LogEntrySerializer(serializers.ModelSerializer):
    """
    default django.contrib.admin.models.LogEntry serializer.
    """

    class Meta:
        model = LogEntry
        fields = '__all__'


class PasswordChangeSerializer(serializers.Serializer):
    """
    Allow changing password by entering the old_password and a new one.
    """
    old_password = serializers.CharField(label=_('Old password'), write_only=True, required=True,
                                         style={'input_type': 'password'})
    new_password1 = serializers.CharField(label=_('New Password'), write_only=True, required=True,
                                          style={'input_type': 'password'})
    new_password2 = serializers.CharField(label=_('New password confirmation'), write_only=True, required=True,
                                          style={'input_type': 'password'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.error_messages.update({
            'password_mismatch': _('The two password fields didn’t match.'),
            'password_incorrect': _("Your old password was entered incorrectly. Please enter it again."),
        })

    def validate(self, data):
        user = self.context['user']

        old_password = data['old_password']
        if not user.check_password(old_password):
            raise serializers.ValidationError(
                self.error_messages['password_incorrect'],
                code='password_incorrect',
            )

        password1 = data.get('new_password1')
        password2 = data.get('new_password2')

        if password1 and password2 and password1 != password2:
            raise serializers.ValidationError(
                self.error_messages['password_mismatch'],
                code='password_mismatch'
            )

        return data

    def save(self, commit=True):
        password = self.validated_data['new_password1']
        user = self.context['user']
        user.set_password(password)
        if commit:
            user.save()
        return user


class ActionSerializer(serializers.Serializer):
    """
    checks that a valid action is selected
    """
    action = serializers.ChoiceField(choices=[("", "---------"), ])
    selected_ids = serializers.MultipleChoiceField(choices=[('', '')])
    select_across = serializers.BooleanField(required=False, default=0)
