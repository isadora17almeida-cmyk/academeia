# ACADEME.IA — link para Mac, Windows, celular e outros sistemas

## 1. Entenda a diferença

`http://127.0.0.1:8000/` só funciona no computador onde o Django está rodando. No celular, `127.0.0.1` aponta para o próprio celular, não para o Mac/Windows.

Para acessar de outros dispositivos, existem duas opções:

1. **Link local na mesma rede Wi-Fi:** funciona em casa/faculdade, mas só para aparelhos conectados à mesma rede.
2. **Link público na internet:** funciona em Mac, Windows, Android, iPhone, tablet e qualquer lugar. Para isso, o projeto precisa ser hospedado em uma plataforma como Render, Railway, Fly.io, VPS etc.

## 2. Link local para celular na mesma rede Wi-Fi

### macOS

Dê duplo clique em:

```text
start_rede_mac.command
```

O Terminal vai mostrar algo parecido com:

```text
Acesse no celular ou outro computador na MESMA rede Wi-Fi: http://192.168.1.23:8000/
```

No celular, conecte no mesmo Wi-Fi e abra esse endereço.

Se o macOS pedir permissão de rede/firewall, aceite.

### Windows

Dê duplo clique em:

```text
start_rede_windows.bat
```

Depois descubra seu IP com:

```bat
ipconfig
```

Procure `Endereço IPv4` e acesse no celular:

```text
http://SEU-IPV4:8000/
```

Exemplo:

```text
http://192.168.1.50:8000/
```

### Linux

Rode:

```bash
./start_rede_linux.sh
```

## 3. Link público para qualquer sistema

Esta versão já vem pronta para deploy com:

- `Procfile`
- `render.yaml`
- `build.sh`
- `runtime.txt`
- `gunicorn`
- `whitenoise`
- leitura automática de `RENDER_EXTERNAL_HOSTNAME`
- suporte a `DATABASE_URL`

### Deploy sugerido no Render

1. Crie uma conta no GitHub.
2. Crie um repositório novo, por exemplo `academeia`.
3. Envie a pasta do projeto para esse repositório.
4. Entre no Render.
5. Crie um **New Web Service** ou **Blueprint** usando o repositório.
6. Use estes comandos se o Render pedir manualmente:

Build Command:

```bash
./build.sh
```

Start Command:

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

7. Cadastre as variáveis de ambiente:

```env
SECRET_KEY=uma-chave-grande-e-secreta
DEBUG=false
AI_PROVIDER=groq
GROQ_API_KEY=sua_chave_groq
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TRANSCRIPTION_MODEL=whisper-large-v3
TRANSCRIPTION_ALWAYS_CHUNK=true
TRANSCRIPTION_LANGUAGE=pt
```

8. Após o deploy, o Render vai gerar um link parecido com:

```text
https://academeia.onrender.com
```

Esse é o link universal para celular, Mac, Windows e qualquer navegador.

## 4. Observação importante sobre arquivos grandes

Transcrição de aulas em áudio/vídeo exige processamento pesado e arquivos grandes. Em hospedagens gratuitas, uploads longos podem falhar por limite de tempo, memória ou armazenamento. Para uso sério, use um plano com mais memória, armazenamento persistente e, idealmente, fila assíncrona.

## 5. Checklist se não abrir no celular

- O computador e o celular estão na mesma rede Wi-Fi.
- O servidor foi iniciado com `0.0.0.0:8000`, não com `127.0.0.1:8000`.
- Você abriu no celular o IP do computador, por exemplo `http://192.168.1.23:8000/`.
- O firewall do Mac/Windows permitiu conexões.
- A rede não é uma rede pública que bloqueia comunicação entre aparelhos.
