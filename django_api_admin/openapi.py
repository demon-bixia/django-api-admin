from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiResponse, OpenApiExample


User = {
    "id": 1,
    "last_login": "2025-01-25T13:00:49.925221Z",
    "is_superuser": True,
    "username": "ms",
    "first_name": "Muhammad",
    "last_name": "Salah",
    "email": "ms@email.com",
    "is_staff": True,
    "is_active": True,
    "date_joined": "2025-01-24T11:43:43.500792Z",
    "groups": [],
    "user_permissions": []
}

ChangeList = {
    'config': {
        'actions_on_top': True,
        'actions_on_bottom': False,
        'actions_selection_counter': True,
        'empty_value_display': '-',
        'list_display': [
            'name', 'age', 'user', 'is_old_enough', 'title', 'gender'
        ],
        'list_display_links': ['name'],
        'list_editable': ['title'],
        'exclude': ['gender'],
        'show_full_result_count': True,
        'list_per_page': 6,
        'list_max_show_all': 200,
        'date_hierarchy': 'date_joined',
        'search_help_text': None,
        'sortable_by': None,
        'search_fields': ['name', 'publisher__name'],
        'preserve_filters': True,
        'full_count': 1,
        'result_count': 1,
        'action_choices': [
            ['delete_selected', 'Delete selected authors'],
            ['make_old', 'make all authors old'],
            ['make_young', 'make all authors young']
        ],
        'filters': [
            {
                'title': 'is vip',
                'choices': [
                    {'selected': True, 'query_string': '?', 'display': 'All'},
                    {'selected': False, 'query_string': '?is_vip__exact=1',
                        'display': 'Yes'},
                    {'selected': False, 'query_string': '?is_vip__exact=0',
                        'display': 'No'}
                ]
            },
            {
                'title': 'age',
                'choices': [
                    {'selected': True, 'query_string': '?', 'display': 'All'},
                    {'selected': False, 'query_string': '?age__exact=60',
                        'display': 'senior'},
                    {'selected': False, 'query_string': '?age__exact=1',
                        'display': 'baby'},
                    {'selected': False, 'query_string': '?age__exact=2',
                        'display': 'also a baby'}
                ]
            }
        ],
        'list_display_fields': ['name', 'age', 'user', 'title'],
        'editing_fields': {
            'title': {
                'type': 'CharField',
                'name': 'title',
                'attrs': {
                    'read_only': False,
                    'write_only': False,
                    'required': False,
                    'default': None,
                    'allow_blank': False,
                    'allow_null': True,
                    'style': {},
                    'label': 'Title',
                    'help_text': None,
                    'initial': '',
                    'max_length': 20,
                    'min_length': None,
                    'trim_whitespace': True
                }
            }
        }
    },
    'columns': [
        {'field': 'name', 'headerName': 'name'},
        {'field': 'age', 'headerName': 'age'},
        {'field': 'user', 'headerName': 'user'},
        {'field': 'is_old_enough', 'headerName': 'is this author old enough'},
        {'field': 'title', 'headerName': 'title'}
    ],
    'rows': [
        {
            'change_url': 'http://localhost:8000/api_admin/test_django_api_admin/author/1/change/',
            'id': 1,
            'cells': {
                'name': 'Muhammad',
                'age': '60',
                'user': 'ms',
                'is_old_enough': True,
                'title': '-'
            }
        }
    ]
}

CrudOperation = {
    "detail": "The author “René Descartes” was changed successfully.",
    "data": {
        "id": 1,
        "name": "Renene Descartes",
        "age": 60,
        "is_vip": True,
        "date_joined": "2025-02-05T04:12:12.191849Z",
        "title": None,
        "user": 1,
        "publisher": [1],
        "pk": 1
    },
}

BulkUpdates = {
    **CrudOperation,
    "updated_inlines": [
        {
            'id': 1,
            'title': 'The book of nine secrets',
            'author': 1,
            'credits': [2], 'pk': 1},
        {'id': 2, 'title': 'purple thunder lightning technique',
         'author': 1, 'credits': [2], 'pk': 2}
    ],
    "deleted_inlines": [{'id': 3, 'title': 'Pro git', 'author': 1, 'credits': [], 'pk': 3}]
}


class APIResponseExamples:
    """
    Provides an example of a successful API response for retrieving form field
    """
    @staticmethod
    def field_attributes():
        return OpenApiExample(
            name=_("Success Response"),
            summary=_("Example of a successful field attribute response"),
            description=_(
                "Retrieve form field attributes for the password change endpoint"),
            value={
                "fields": [
                    {
                        "type": "CharField",
                        "name": "field_name",
                        "attrs": {
                            "read_only": False,
                            "write_only": True,
                            "required": True,
                            "default": None,
                            "allow_blank": False,
                            "allow_null": False,
                            "label": "Field name",
                            "help_text": None,
                            "initial": "",
                            "max_length": None,
                            "min_length": None,
                            "trim_whitespace": True
                        }
                    }
                ]
            },
            status_codes=["200"],
        )


class CommonAPIResponses:
    """Collection of standardized OpenAPI response templates."""

    @staticmethod
    def permission_denied():
        return OpenApiResponse(
            description=_("Permission denied"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Permission Denied"),
                    summary=_("Permission denied response"),
                    value={
                        "detail": _("You do not have permission to perform this action.")
                    },
                    status_codes=["403"]
                )
            ]
        )

    @staticmethod
    def not_found():
        return OpenApiResponse(
            description=_("Resource not found"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Not Found"),
                    summary=_("Resource not found response"),
                    value={
                        "detail": _("The requested resource was not found.")
                    },
                    status_codes=["404"]
                )
            ]
        )

    @staticmethod
    def bad_request():
        return OpenApiResponse(
            description=_("Bad request"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Bad Request"),
                    summary=_("Invalid request parameters or data"),
                    value={
                        "detail": _("The request contains invalid parameters or data.")
                    },
                    status_codes=["400"]
                )
            ]
        )

    @staticmethod
    def unauthorized():
        return OpenApiResponse(
            description=_("Authentication required"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Unauthorized"),
                    summary=_("Missing or invalid authentication credentials"),
                    value={
                        "detail": _("Authentication credentials were not provided.")
                    },
                    status_codes=["401"]
                )
            ]
        )

    @staticmethod
    def method_not_allowed():
        return OpenApiResponse(
            description=_("Method not allowed"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Method Not Allowed"),
                    summary=_("HTTP method not supported"),
                    value={
                        "detail": _("Method not allowed for this endpoint.")
                    },
                    status_codes=["405"]
                )
            ]
        )

    @staticmethod
    def conflict():
        return OpenApiResponse(
            description=_("Resource conflict"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Conflict"),
                    summary=_("Resource conflict detected"),
                    value={
                        "detail": _("The request conflicts with the current state of the target resource.")
                    },
                    status_codes=["409"]
                )
            ]
        )

    @staticmethod
    def server_error():
        return OpenApiResponse(
            description=_("Internal server error"),
            response=dict,
            examples=[
                OpenApiExample(
                    name=_("Server Error"),
                    summary=_("Internal server error occurred"),
                    value={
                        "detail": _("An unexpected error occurred while processing the request.")
                    },
                    status_codes=["500"]
                )
            ]
        )
