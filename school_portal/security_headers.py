from flask import Flask

CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "object-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'"
)


def init_security_headers(app: Flask) -> None:
    @app.after_request
    def add_headers(response):
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(self), geolocation=()")
        if response.mimetype == "text/html":
            # Pages hold children's details: never keep them in a shared cache.
            response.headers.setdefault("Cache-Control", "private, no-store")
        return response
