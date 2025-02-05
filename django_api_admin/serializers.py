from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from django_api_admin.models import LogEntry

UserModel = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserModel
        exclude = ('password',)


class ObtainTokenSerializer(serializers.Serializer):
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
    default LogEntry serializer.
    """
    class Meta:
        model = LogEntry
        fields = '__all__'


class AdminLogRequestSerializer(serializers.Serializer):
    """
    Serializer for the admin log request.
    """
    o = serializers.ChoiceField(
        choices=[
            ('action_time', 'Action Time (Ascending)'),
            ('-action_time', 'Action Time (Descending)')
        ],
        required=False
    )
    object_id = serializers.IntegerField(required=False)


class PasswordChangeSerializer(serializers.Serializer):
    """
    Allow changing password by entering the old_password and a new one.
    """
    old_password = serializers.CharField(
        label=_('Old password'),
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password1 = serializers.CharField(
        label=_('New Password'),
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        label=_('New password confirmation'),
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

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


class ChangeListSerializer(serializers.Serializer):
    """
    validates the changelist querystring
    """
    q = serializers.CharField(required=False, trim_whitespace=False)
    p = serializers.IntegerField(required=False, min_value=1)
    all = serializers.BooleanField(required=False)
    o = serializers.CharField(required=False)
    _to_field = serializers.CharField(required=False)


class AppIndexSerializer(serializers.Serializer):
    app_label = serializers.CharField()

    def validate(self, attrs):
        if attrs['app_label'] not in self.context['registered_app_labels']:
            raise serializers.ValidationError(
                _("finish must occur after start"))
        return super().validate(attrs)


class PermissionsSerializer(serializers.Serializer):
    add = serializers.BooleanField()
    change = serializers.BooleanField()
    delete = serializers.BooleanField()
    view = serializers.BooleanField()


class ModelSerializer(serializers.Serializer):
    name = serializers.CharField()
    object_name = serializers.CharField()
    perms = PermissionsSerializer()
    list_url = serializers.CharField()
    changelist_url = serializers.CharField()
    add_url = serializers.CharField()
    perform_action_url = serializers.CharField()
    view_only = serializers.BooleanField()


class AppSerializer(serializers.Serializer):
    name = serializers.CharField()
    app_label = serializers.CharField()
    app_url = serializers.CharField()
    has_module_perms = serializers.BooleanField()
    models = ModelSerializer(many=True)


class AppListSerializer(serializers.Serializer):
    app_list = AppSerializer(many=True)


class AutoCompleteSerializer(serializers.Serializer):
    app_label = serializers.CharField(required=True)
    model_name = serializers.CharField(required=True)
    field_name = serializers.CharField(required=True)
    term = serializers.CharField(required=False, default="")


class FormatsSerializer(serializers.Serializer):
    DATE_FORMAT = serializers.CharField(allow_blank=False)
    DATETIME_FORMAT = serializers.CharField(allow_blank=False)
    TIME_FORMAT = serializers.CharField(allow_blank=False)
    YEAR_MONTH_FORMAT = serializers.CharField(allow_blank=False)
    MONTH_DAY_FORMAT = serializers.CharField(allow_blank=False)
    SHORT_DATE_FORMAT = serializers.CharField(allow_blank=False)
    SHORT_DATETIME_FORMAT = serializers.CharField(allow_blank=False)
    FIRST_DAY_OF_WEEK = serializers.IntegerField()
    DECIMAL_SEPARATOR = serializers.CharField(allow_blank=False)
    THOUSAND_SEPARATOR = serializers.CharField(allow_blank=False)
    NUMBER_GROUPING = serializers.IntegerField()
    DATE_INPUT_FORMATS = serializers.ListField(
        child=serializers.CharField(allow_blank=False)
    )
    TIME_INPUT_FORMATS = serializers.ListField(
        child=serializers.CharField(allow_blank=False)
    )
    DATETIME_INPUT_FORMATS = serializers.ListField(
        child=serializers.CharField(allow_blank=False)
    )


class CatalogSerializer(serializers.Serializer):
    catalog = serializers.DictField(child=serializers.CharField())


class LanguageCatalogSerializer(serializers.Serializer):
    catalog = CatalogSerializer()
    formats = FormatsSerializer()
    plural = serializers.CharField(allow_null=True, required=False)


class FieldAttributesSerializer(serializers.Serializer):
    read_only = serializers.BooleanField(default=False)
    write_only = serializers.BooleanField(default=False)
    required = serializers.BooleanField(default=True)
    default = serializers.CharField(allow_null=True, required=False)
    allow_blank = serializers.BooleanField(default=False)
    allow_null = serializers.BooleanField(default=False)
    style = serializers.JSONField(default=dict)
    label = serializers.CharField(allow_null=True, required=False)
    help_text = serializers.CharField(allow_null=True, required=False)
    initial = serializers.CharField(default="", required=False)
    max_length = serializers.IntegerField(allow_null=True, required=False)
    min_length = serializers.IntegerField(allow_null=True, required=False)
    trim_whitespace = serializers.BooleanField(default=True)
    min_value = serializers.FloatField(allow_null=True, required=False)
    max_value = serializers.FloatField(allow_null=True, required=False)
    format = serializers.CharField(allow_null=True, required=False)
    input_formats = serializers.ListField(
        child=serializers.CharField(allow_null=True, required=False)
    )
    choices = serializers.ListField(
        child=serializers.ListField(
            child=serializers.CharField()
        )
    )
    html_cutoff = serializers.IntegerField()
    html_cutoff_text = serializers.CharField()
    allow_empty_files = serializers.BooleanField()
    use_url = serializers.BooleanField()
    allow_empty = serializers.BooleanField()
    child = serializers.JSONField()


class FieldSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    attrs = FieldAttributesSerializer()


class FormFieldsSerializer(serializers.Serializer):
    fields = FieldSerializer(many=True)


class TokensSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    access = serializers.CharField()


class ObtainTokenResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    user = UserSerializer()
    tokens = TokensSerializer()


class SiteContextSerializer(serializers.Serializer):
    site_title = serializers.CharField()
    site_header = serializers.CharField()
    site_url = serializers.CharField()
    has_permission = serializers.BooleanField()
    available_apps = AppSerializer(many=True)
    is_nav_siderbar_enabled = serializers.BooleanField()


class ActionChoiceSerializer(serializers.Serializer):
    action = serializers.CharField()
    description = serializers.CharField()


class FilterChoiceSerializer(serializers.Serializer):
    selected = serializers.BooleanField()
    query_string = serializers.CharField()
    display = serializers.CharField()


class FilterSerializer(serializers.Serializer):
    title = serializers.CharField()
    choices = FilterChoiceSerializer(many=True)


class EditingFieldSerializer(serializers.Serializer):
    type = serializers.CharField()
    name = serializers.CharField()
    attrs = serializers.DictField()


class ConfigSerializer(serializers.Serializer):
    actions_on_top = serializers.BooleanField()
    actions_on_bottom = serializers.BooleanField()
    actions_selection_counter = serializers.BooleanField()
    empty_value_display = serializers.CharField()
    list_display = serializers.ListField(child=serializers.CharField())
    list_display_links = serializers.ListField(child=serializers.CharField())
    list_editable = serializers.ListField(child=serializers.CharField())
    exclude = serializers.ListField(child=serializers.CharField())
    show_full_result_count = serializers.BooleanField()
    list_per_page = serializers.IntegerField()
    list_max_show_all = serializers.IntegerField()
    date_hierarchy = serializers.CharField()
    search_help_text = serializers.CharField(allow_null=True)
    sortable_by = serializers.ListField(
        child=serializers.CharField(), allow_null=True)
    search_fields = serializers.ListField(child=serializers.CharField())
    preserve_filters = serializers.BooleanField()
    full_count = serializers.IntegerField()
    result_count = serializers.IntegerField()
    action_choices = ActionChoiceSerializer(many=True)
    filters = FilterSerializer(many=True)
    list_display_fields = serializers.ListField(child=serializers.CharField())
    editing_fields = serializers.DictField(child=EditingFieldSerializer())


class ColumnSerializer(serializers.Serializer):
    field = serializers.CharField()
    headerName = serializers.CharField()


class CellSerializer(serializers.Serializer):
    name = serializers.CharField()
    age = serializers.CharField()
    user = serializers.CharField()
    is_old_enough = serializers.BooleanField()
    title = serializers.CharField()


class RowSerializer(serializers.Serializer):
    change_url = serializers.URLField()
    id = serializers.IntegerField()
    cells = CellSerializer()


class ChangelistResponseSerializer(serializers.Serializer):
    config = ConfigSerializer()
    columns = ColumnSerializer(many=True)
    rows = RowSerializer(many=True)


class BulkUpdatesResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()
    updated_inlines = serializers.ListField(child=serializers.DictField())
    deleted_inlines = serializers.ListField(child=serializers.DictField())


class ResponseMessageSerializer(serializers.Serializer):
    detail = serializers.CharField()
