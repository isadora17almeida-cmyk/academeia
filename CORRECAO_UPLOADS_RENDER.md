# Correção para uploads longos no Render

Esta versão ajusta o servidor para reduzir quedas 502 durante uploads/transcrições:

- `start.sh` usa Gunicorn com `gthread`, timeout de 3600s e logs em stdout.
- Django usa `TemporaryFileUploadHandler` para não guardar arquivos grandes em memória.
- `MaxRequestBodySizeMiddleware` rejeita uploads acima de `MAX_REQUEST_BODY_MB` antes de ler todo o corpo da requisição.

Variáveis recomendadas no Render:

```env
WEB_TIMEOUT=3600
WEB_GRACEFUL_TIMEOUT=3600
WEB_THREADS=2
WEB_CONCURRENCY=1
MAX_UPLOAD_MB=250
MAX_REQUEST_BODY_MB=250
```

Para aulas muito longas, prefira M4A/MP3 comprimido ou divida o áudio em partes menores antes do upload.
