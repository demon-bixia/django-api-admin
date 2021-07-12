class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class ApiAdminSite:
    """
    Encapsulates an instance of the django admin application.
    """