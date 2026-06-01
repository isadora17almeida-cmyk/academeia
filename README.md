# ACADEME.IA

**ACADEME.IA** é uma plataforma pessoal de estudos com inteligência artificial para estudantes de **Direito** e **Medicina**. O projeto foi criado em **Python + Django + SQLite**, com interface dark neon, login, dashboard, geração de resumos, questões, transcrição, biblioteca, flashcards, simulados, plano de estudos, perfil e exportação em Word, PDF e TXT.

Não há planos pagos, assinatura, cobrança, checkout ou integração de pagamento.

## Arquitetura resumida

```text
academeia/
├── manage.py
├── requirements.txt
├── .env.example
├── README.md
├── config/                 # Configurações Django
├── accounts/               # Cadastro, login, perfil
├── core/                   # Landing page e páginas institucionais
├── studies/                # Módulos acadêmicos e serviços de IA/exportação
├── static/                 # CSS, JS, imagens
├── media/                  # Uploads e exports gerados
└── templates/              # Templates globais e parciais
```

## Funcionalidades

- Landing page futurista com visual premium neon.
- Cadastro, login, logout e perfil.
- Dashboard com estatísticas e últimos materiais.
- Geração de resumos para Direito, Medicina e Geral.
- Geração de questões com gabarito e explicação.
- Transcrição de aulas com upload de áudio/vídeo e integração opcional com IA.
- Biblioteca com filtros, pastas, favoritos e exportação.
- Flashcards com revisão e marcação de acerto/erro.
- Simulados com questões e resultado básico.
- Plano de estudos personalizado.
- Exportação em `.docx`, `.pdf` e `.txt`.
- Camada `ai_service.py` com fallback local quando a chave de IA não está configurada.

## Instalação

No Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

No macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Acesse:

```text
http://127.0.0.1:8000/
```

## Configurar IA no `.env`

Edite o arquivo `.env`:

```env
OPENAI_API_KEY=sua_chave_aqui
OPENAI_MODEL=gpt-4o-mini
AI_PROVIDER=openai
```

Se `OPENAI_API_KEY` ficar vazio, o sistema entra em modo local demonstrativo e gera conteúdos estruturados sem chamar API externa. Assim você pode testar tudo imediatamente.

## Banco de dados

O projeto usa SQLite por padrão. Para criar as tabelas:

```bash
python manage.py makemigrations
python manage.py migrate
```

A estrutura está separada em apps para facilitar migração futura para PostgreSQL.

## Usuário administrador

```bash
python manage.py createsuperuser
```

Depois acesse:

```text
http://127.0.0.1:8000/admin/
```

## Testar as funções principais

1. Crie uma conta em `/accounts/register/`.
2. Entre no dashboard.
3. Gere um resumo com o assunto “Obrigação de fazer no Direito Civil”.
4. Gere questões sobre “Pâncreas”.
5. Envie um arquivo na tela de Transcrição. Sem API, será gerada uma transcrição demonstrativa.
6. Abra a Biblioteca para visualizar os materiais salvos.
7. Use os botões de exportação para baixar Word, PDF ou TXT.
8. Crie flashcards, um simulado e um plano de estudos.

## Observações técnicas

- As páginas internas exigem autenticação.
- A chave de IA nunca é exposta no frontend.
- Uploads ficam em `media/uploads/`.
- Exportações ficam em `media/exports/`.
- CSRF está ativo nos formulários.
- O limite de upload pode ser configurado em `MAX_UPLOAD_MB`.

## Estrutura de IA

Os serviços ficam em `studies/services/`:

- `ai_service.py`: resumos, questões, flashcards, simulados, revisão de transcrição e plano de estudos.
- `transcription_service.py`: processamento de upload e transcrição.
- `export_service.py`: geração de DOCX, PDF e TXT.
- `study_plan_service.py`: cronograma diário local.

## Próximos upgrades sugeridos

- Fila assíncrona com Celery/RQ para transcrições longas.
- PostgreSQL em produção.
- Armazenamento externo para arquivos grandes.
- Editor rico de conteúdo.
- Revisão espaçada com algoritmo SM-2 para flashcards.

## Atualização: transcrição separada do resumo

O módulo de transcrição agora salva dois campos separados:

- **Transcrição do professor:** texto puro da fala transcrita, sem resumo.
- **Resumo da aula:** material de estudo gerado automaticamente a partir da transcrição.

Na tela `Transcrição de Aulas`, depois do envio do arquivo, o sistema exibe primeiro a seção **Transcrição do professor** e abaixo a seção **Resumo da aula**. As transcrições recentes também possuem o link **Ver transcrição**, que abre a tela completa da aula.

Se você já tiver criado o banco antes desta atualização, rode:

```bash
python manage.py makemigrations
python manage.py migrate
```

## Atualização: menu lateral, perfil e resumo

Esta versão adiciona:

- Botão no topo para recolher/abrir o menu lateral. Em telas pequenas, o menu abre como gaveta lateral.
- Cartão de conta no canto superior direito, com foto de perfil quando cadastrada ou iniciais do usuário quando não houver imagem.
- Upload de foto no perfil do usuário.
- Renderização visual de markdown nos resumos, transcrições e planos, sem mostrar os símbolos `#` e `##` como texto cru.
- Geração de resumo mais tolerante a erro: se a API externa falhar, o sistema ainda mostra um resumo local estruturado.
- Suporte opcional ao GroqCloud para resumos, questões, flashcards e transcrição.

### Usar GroqCloud

No arquivo `.env`, configure:

```env
AI_PROVIDER=groq
GROQ_API_KEY=sua_chave_groq_aqui
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3
```

Depois reinicie o servidor:

```bash
python manage.py runserver
```

Se a chave estiver errada, ausente ou sem limite disponível, o ACADEME.IA continua funcionando no modo local demonstrativo.

## Transcrição completa de aulas longas

A partir desta versão, a transcrição tenta preservar a aula completa.

- Arquivos `.txt` são importados integralmente.
- Áudio/vídeo usa a chave configurada em `.env`.
- Se `ffmpeg` e `ffprobe` estiverem instalados, arquivos longos são divididos em partes menores com sobreposição e todas as partes são transcritas e juntadas. Essa estratégia evita que a API devolva apenas o início da aula.

No macOS, instale o ffmpeg com:

```bash
brew install ffmpeg
```

Variáveis úteis no `.env`:

```env
TRANSCRIPTION_CHUNK_SECONDS=180
TRANSCRIPTION_OVERLAP_SECONDS=5
TRANSCRIPTION_DIRECT_MAX_MB=10
TRANSCRIPTION_FORCE_CHUNK_AFTER_SECONDS=120
TRANSCRIPTION_ALWAYS_CHUNK=true
TRANSCRIPTION_LANGUAGE=pt
```

Se a tela avisar "modo demonstrativo", significa que a API de IA não foi configurada ou falhou; nesse caso, o texto exibido não é a transcrição real completa da aula.


## Atualização: transcrição reforçada sem corte

Esta versão força o processamento por blocos em aulas acima de 2 minutos ou arquivos maiores que 10 MB. Cada bloco é convertido para FLAC mono 16 kHz, transcrito separadamente e unido em sequência com marcação de partes, por exemplo `[Parte 1/12]`.

Para reprocessar uma aula já enviada, abra a transcrição e clique em **Retranscrever aula completa**. O sistema usará o arquivo original salvo em `media/uploads/transcriptions/`.

Se o resultado ainda aparecer curto, confirme estes pontos:

1. `GROQ_API_KEY` ou `OPENAI_API_KEY` está preenchida no `.env`.
2. `AI_PROVIDER=groq` ou `AI_PROVIDER=openai` está correto.
3. `ffmpeg -version` funciona no Terminal.
4. O servidor foi reiniciado depois de alterar o `.env`.
5. A aula foi enviada novamente ou retranscrita pelo botão **Retranscrever aula completa**.
