from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


class MaxRequestBodySizeMiddleware:
    """Recusa uploads grandes demais antes de o Django tentar ler todo o corpo.

    Isso evita que o worker do Gunicorn seja abortado durante uploads longos no Render.
    O limite é controlado por MAX_REQUEST_BODY_MB.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                content_length = int(request.META.get("CONTENT_LENGTH") or 0)
            except (TypeError, ValueError):
                content_length = 0
            max_mb = int(getattr(settings, "MAX_REQUEST_BODY_MB", 250))
            max_bytes = max_mb * 1024 * 1024
            if max_bytes and content_length and content_length > max_bytes:
                html = f"""
                <!doctype html>
                <html lang='pt-br'>
                <head><meta charset='utf-8'><title>Arquivo muito grande</title></head>
                <body style="font-family: system-ui, -apple-system, Segoe UI, sans-serif; padding: 40px; line-height: 1.5;">
                  <h1>Arquivo muito grande</h1>
                  <p>O arquivo enviado tem aproximadamente <strong>{content_length / 1024 / 1024:.1f} MB</strong>.</p>
                  <p>O limite atual deste servidor é <strong>{max_mb} MB</strong>.</p>
                  <p>Para aulas longas, divida o áudio em partes menores ou comprima o arquivo para M4A/MP3 antes de enviar.</p>
                  <p><a href="/app/transcricoes/">Voltar para transcrições</a></p>
                </body>
                </html>
                """
                return HttpResponse(html, status=413)
        return self.get_response(request)
