import logging

class AccessLogMiddleware:
    """Middleware to log every request with remote IP, method, path, and response status."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("access")

    def __call__(self, request):
        response = self.get_response(request)

        # Extract necessary information
        remote_addr = request.META.get("REMOTE_ADDR", "-")
        request_method = request.method
        path = request.get_full_path()
        status_code = response.status_code

        # Log with extra parameters
        self.logger.info(
            f"{remote_addr} {request_method} {path} {status_code}"
        )

        return response
