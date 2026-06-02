# Correção: resumo fiel sem estourar limite da Groq

Esta versão corrige o erro:

```text
HTTP 413 rate_limit_exceeded / tokens per minute
```

A transcrição completa pode ficar muito grande. Antes, o sistema enviava a transcrição extensa em uma única chamada para o modelo de texto da Groq. Em contas com limite baixo de tokens por minuto, isso fazia o resumo falhar.

## O que mudou

- O resumo agora usa uma fonte condensada da transcrição completa.
- O sistema não mostra mais erro técnico bruto como se fosse resumo.
- Se a IA estiver indisponível ou bater limite, o app gera um resumo local fiel usando trechos reais da transcrição.
- A transcrição recebe um prompt contextual curto para melhorar termos jurídicos/médicos.

## Variáveis recomendadas no Render

```env
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3-turbo
TRANSCRIPTION_ALWAYS_CHUNK=true
TRANSCRIPTION_CHUNK_SECONDS=45
TRANSCRIPTION_OVERLAP_SECONDS=5
TRANSCRIPTION_RETRY_ATTEMPTS=6
TRANSCRIPTION_LANGUAGE=pt
TRANSCRIPTION_PROMPT=Aula de Direito em português do Brasil. Preserve a fala do professor e atenção a termos jurídicos.
SUMMARY_DIRECT_CHARS=9000
SUMMARY_SOURCE_MAX_CHARS=9000
SUMMARY_MAX_OUTPUT_TOKENS=1200
```

Se a transcrição de termos jurídicos ficar muito imprecisa, teste `GROQ_TRANSCRIPTION_MODEL=whisper-large-v3`. Se voltar a dar 502, use novamente `whisper-large-v3-turbo`.
