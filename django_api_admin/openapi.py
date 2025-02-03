from drf_spectacular.utils import OpenApiResponse, OpenApiExample


class CommonAPIResponses:
    """Collection of standardized OpenAPI response templates."""

    @staticmethod
    def permission_denied():
        return OpenApiResponse(
            description="Permission denied",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Permission Denied",
                    summary="Permission denied response",
                    value={
                        "detail": "You do not have permission to perform this action."
                    },
                    status_codes=["403"]
                )
            ]
        )

    @staticmethod
    def not_found():
        return OpenApiResponse(
            description="Resource not found",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Not Found",
                    summary="Resource not found response",
                    value={
                        "detail": "The requested resource was not found."
                    },
                    status_codes=["404"]
                )
            ]
        )

    @staticmethod
    def bad_request():
        return OpenApiResponse(
            description="Bad request",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Bad Request",
                    summary="Invalid request parameters or data",
                    value={
                        "detail": "The request contains invalid parameters or data."
                    },
                    status_codes=["400"]
                )
            ]
        )

    @staticmethod
    def unauthorized():
        return OpenApiResponse(
            description="Authentication required",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Unauthorized",
                    summary="Missing or invalid authentication credentials",
                    value={
                        "detail": "Authentication credentials were not provided."
                    },
                    status_codes=["401"]
                )
            ]
        )

    @staticmethod
    def method_not_allowed():
        return OpenApiResponse(
            description="Method not allowed",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Method Not Allowed",
                    summary="HTTP method not supported",
                    value={
                        "detail": "Method not allowed for this endpoint."
                    },
                    status_codes=["405"]
                )
            ]
        )

    @staticmethod
    def conflict():
        return OpenApiResponse(
            description="Resource conflict",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Conflict",
                    summary="Resource conflict detected",
                    value={
                        "detail": "The request conflicts with the current state of the target resource."
                    },
                    status_codes=["409"]
                )
            ]
        )

    @staticmethod
    def server_error():
        return OpenApiResponse(
            description="Internal server error",
            response=dict,
            examples=[
                OpenApiExample(
                    name="Server Error",
                    summary="Internal server error occurred",
                    value={
                        "detail": "An unexpected error occurred while processing the request."
                    },
                    status_codes=["500"]
                )
            ]
        )

    @classmethod
    def get_common_responses(cls):
        """Returns a dictionary of common responses used in most endpoints."""
        return {
            "400": cls.bad_request(),
            "401": cls.unauthorized(),
            "403": cls.permission_denied(),
            "404": cls.not_found(),
            "405": cls.method_not_allowed(),
            "409": cls.conflict(),
            "500": cls.server_error()
        }
