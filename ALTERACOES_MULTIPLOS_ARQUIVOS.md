# Alterações — múltiplos arquivos

Esta atualização adiciona suporte para selecionar vários arquivos em uma única ação.

## Onde foi aplicado

- **Transcrição de aulas**: agora aceita vários áudios/vídeos/TXT no mesmo envio e junta tudo em uma transcrição contínua do professor.
- **Gerar resumo**: agora aceita vários PDFs/materiais e vários áudios/vídeos da mesma aula.
- **Criar questões**: agora aceita vários PDFs/TXT como base.
- **Flashcards**: agora aceita vários PDFs/TXT como base.
- **Simulados**: agora aceita vários PDFs/TXT como base.

## Observação importante

Na transcrição, os arquivos são processados na ordem escolhida no formulário. A tela principal mostra apenas a fala limpa do professor, sem cabeçalhos técnicos de arquivo ou marcações de parte.

## Variáveis recomendadas no Render

```env
MAX_UPLOAD_MB=250
MAX_TOTAL_UPLOAD_MB=750
MAX_REQUEST_BODY_MB=750
WEB_TIMEOUT=3600
WEB_GRACEFUL_TIMEOUT=3600
WEB_THREADS=2
WEB_CONCURRENCY=1
```
