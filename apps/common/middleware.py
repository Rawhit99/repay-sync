from django.utils.deprecation import MiddlewareMixin

from apps.common.request_context import bind_request_state, clear_request_state


class RequestContextMiddleware(MiddlewareMixin):
    """Bind per-request caches for access services and hierarchy reuse."""

    def process_request(self, request):
        bind_request_state()

    def process_response(self, request, response):
        clear_request_state()
        return response

    def process_exception(self, request, exception):
        clear_request_state()
