from django.conf import settings


class SecurityHeadersMiddleware:
    """Dodaje nagłówki bezpieczeństwa i SEO do każdej odpowiedzi."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.csp = getattr(settings, 'CONTENT_SECURITY_POLICY', '')
        self.pp = getattr(settings, 'PERMISSIONS_POLICY', '')

    def __call__(self, request):
        response = self.get_response(request)
        if self.csp:
            response['Content-Security-Policy'] = self.csp
        if self.pp:
            response['Permissions-Policy'] = self.pp
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        return response
