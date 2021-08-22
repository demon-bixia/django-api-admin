from rest_framework.pagination import PageNumberPagination


class AdminResultsListPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    page_query_param = 'p'
    max_page_size = 100
