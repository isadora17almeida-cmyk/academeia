# Correção: `_build_transcription_prompt` não definido

Esta versão corrige o erro:

```text
name '_build_transcription_prompt' is not defined
```

A função foi adicionada ao serviço de transcrição. Ela monta apenas um contexto curto para o Whisper/Groq, sem gerar resumo e sem inventar conteúdo. O objetivo continua sendo registrar a fala do professor na ordem da aula.

Após atualizar, envie para o GitHub e faça novo deploy no Render.
