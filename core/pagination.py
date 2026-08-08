from rest_framework.pagination import PageNumberPagination


class DefaultPageNumberPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def paginated_response(view, request, queryset, serializer_class, *, context=None, status=None, results_key=None):
    paginator = DefaultPageNumberPagination()
    page = paginator.paginate_queryset(queryset, request, view=view)
    serializer = serializer_class(
        page if page is not None else queryset,
        many=True,
        context=context or {"request": request},
    )
    response = paginator.get_paginated_response(serializer.data) if page is not None else None
    if response is not None and results_key:
        response.data[results_key] = response.data["results"]
    if response is None:
        from rest_framework.response import Response

        response = Response(serializer.data)
    if status is not None:
        response.status_code = status
    return response


def paginated_data_response(view, request, items, *, status=None, results_key=None):
    paginator = DefaultPageNumberPagination()
    page = paginator.paginate_queryset(items, request, view=view)
    response = paginator.get_paginated_response(page if page is not None else items)
    if results_key:
        response.data[results_key] = response.data["results"]
    if status is not None:
        response.status_code = status
    return response
