from rest_framework.pagination import PageNumberPagination
from math import ceil


class AdminResultsListPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    page_query_param = 'p'

    def get_num_of_pages(self, list_of_items):
        return ceil(len(list_of_items) / self.page_size)

    def get_num_of_items(self, list_of_items):
        return len(list_of_items)


class AdminLogPagination(PageNumberPagination):
    page_size = 8
    page_size_query_param = 'page_size'
    page_query_param = 'p'
