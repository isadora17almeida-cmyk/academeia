# Correção de transcrição Groq 502

Esta versão evita salvar transcrição demonstrativa e trata falhas temporárias HTTP 502/503/504 da Groq com novas tentativas.

Configuração recomendada no Render:

```env
AI_PROVIDER=groq
GROQ_API_KEY=sua_chave_groq_real
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
TRANSCRIPTION_ALWAYS_CHUNK=true
TRANSCRIPTION_CHUNK_SECONDS=45
TRANSCRIPTION_OVERLAP_SECONDS=5
TRANSCRIPTION_FORCE_CHUNK_AFTER_SECONDS=45
TRANSCRIPTION_RETRY_ATTEMPTS=6
TRANSCRIPTION_LANGUAGE=pt
```

Se quiser maior precisão e sua conta Groq estiver estável, troque `GROQ_TRANSCRIPTION_MODEL` para `whisper-large-v3`.

Para testar, envie uma aula curta primeiro. Depois envie uma aula longa.
