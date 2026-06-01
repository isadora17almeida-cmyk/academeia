from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests
from django.conf import settings

from .ai_service import has_configured_ai


AUDIO_VIDEO_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.mp4', '.aac', '.ogg', '.webm', '.mov', '.mpeg', '.mpga', '.flac'}
TEXT_EXTENSIONS = {'.txt'}
FALLBACK_PREFIX = '# Transcrição demonstrativa'


def transcribe_uploaded_file(uploaded_file, *, title: str, subject: str = '', area: str = 'geral') -> str:
    """Transcreve um arquivo enviado preservando aulas longas.

    Estratégia da versão reforçada:
    - TXT: lê o texto inteiro, sem corte.
    - Áudio/vídeo curto: tenta transcrição direta.
    - Áudio/vídeo longo ou grande: usa ffmpeg para dividir em blocos pequenos
      com sobreposição, transcreve todas as partes e junta o resultado.
    - Se a transcrição direta parecer curta demais para a duração do arquivo,
      reprocessa automaticamente por blocos.
    """
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        raw = uploaded_file.read()
        try:
            return raw.decode('utf-8')
        except UnicodeDecodeError:
            return raw.decode('latin-1', errors='ignore')

    if suffix not in AUDIO_VIDEO_EXTENSIONS:
        raise ValueError('Formato de arquivo não suportado para transcrição.')

    if not has_configured_ai():
        raise RuntimeError(
            'A chave de IA não está configurada. No Render, adicione AI_PROVIDER=groq e GROQ_API_KEY com sua chave real.'
        )

    # Não retornamos mais transcrição demonstrativa quando a API falha.
    # Isso evita salvar texto falso como se fosse a fala do professor.
    return _transcribe_complete_with_configured_provider(uploaded_file, suffix=suffix)


def extract_transcript_only(text: str) -> str:
    """Extrai somente a fala da aula sem sacrificar conteúdo legítimo."""
    if not text:
        return ''
    cleaned = text.strip()

    fallback_markers = [
        '## Texto transcrito do professor',
        '## Texto transcrito de exemplo',
        '### Texto transcrito do professor',
        '### Texto transcrito de exemplo',
    ]
    for marker in fallback_markers:
        if marker in cleaned:
            cleaned = cleaned.split(marker, 1)[1].strip()
            break

    technical_markers = [
        '\n\nObservação técnica:',
        '\nObservação técnica:',
    ]
    for marker in technical_markers:
        pos = cleaned.find(marker)
        if pos > 0:
            cleaned = cleaned[:pos].strip()

    explicit_separators = [
        '\n--- RESUMO GERADO ---',
        '\n--- Resumo gerado ---',
        '\n=== RESUMO GERADO ===',
    ]
    for marker in explicit_separators:
        pos = cleaned.find(marker)
        if pos > 0:
            cleaned = cleaned[:pos].strip()

    return cleaned.strip()


def is_demo_transcription(text: str) -> bool:
    return bool(text and text.lstrip().startswith(FALLBACK_PREFIX))


def _transcribe_complete_with_configured_provider(uploaded_file, *, suffix: str) -> str:
    with tempfile.TemporaryDirectory(prefix='academeia_transcricao_') as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        source_path = temp_dir / f'entrada{suffix}'
        _save_uploaded_file(uploaded_file, source_path)

        chunk_seconds = max(30, int(getattr(settings, 'TRANSCRIPTION_CHUNK_SECONDS', 180)))
        overlap_seconds = max(0, int(getattr(settings, 'TRANSCRIPTION_OVERLAP_SECONDS', 5)))
        direct_max_mb = float(getattr(settings, 'TRANSCRIPTION_DIRECT_MAX_MB', 10))
        force_chunk_after_seconds = int(getattr(settings, 'TRANSCRIPTION_FORCE_CHUNK_AFTER_SECONDS', 120))
        always_chunk = str(getattr(settings, 'TRANSCRIPTION_ALWAYS_CHUNK', 'false')).lower() in {'1', 'true', 'yes', 'sim'}

        file_size_mb = source_path.stat().st_size / (1024 * 1024)
        ffmpeg_path = _ffmpeg_binary()
        has_ffmpeg = bool(ffmpeg_path)
        duration = _media_duration_seconds(source_path) if has_ffmpeg else None

        # Para arquivos maiores/longos, ffmpeg é obrigatório para evitar cortes silenciosos.
        should_chunk_first = bool(
            has_ffmpeg and (
                always_chunk
                or file_size_mb > direct_max_mb
                or (duration and duration >= force_chunk_after_seconds)
            )
        )

        if should_chunk_first:
            return _transcribe_in_chunks(
                source_path=source_path,
                temp_dir=temp_dir,
                duration=duration,
                chunk_seconds=chunk_seconds,
                overlap_seconds=overlap_seconds,
            )

        direct_text = _transcribe_file_path(source_path).strip()

        # Proteção extra: se o retorno direto for pequeno demais para a duração,
        # reprocessa em blocos. Isso resolve casos em que a API devolve só o começo.
        if has_ffmpeg and duration and _looks_incomplete(direct_text, duration):
            chunked_text = _transcribe_in_chunks(
                source_path=source_path,
                temp_dir=temp_dir,
                duration=duration,
                chunk_seconds=chunk_seconds,
                overlap_seconds=overlap_seconds,
            ).strip()
            if len(chunked_text) > len(direct_text):
                return chunked_text

        return direct_text


def _save_uploaded_file(uploaded_file, destination: Path) -> None:
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    with destination.open('wb') as output:
        if hasattr(uploaded_file, 'chunks'):
            for chunk in uploaded_file.chunks():
                output.write(chunk)
        else:
            output.write(uploaded_file.read())
    try:
        uploaded_file.seek(0)
    except Exception:
        pass


def _has_binary(name: str) -> bool:
    return shutil.which(name) is not None


def _ffmpeg_binary() -> str | None:
    """Retorna um ffmpeg disponível no sistema ou o binário empacotado pelo Python.

    Em serviços cloud como Render, o ffmpeg do sistema pode não estar instalado.
    O pacote imageio-ffmpeg baixa/fornece um binário funcional no ambiente Python,
    evitando erro 500 durante transcrições longas que precisam ser divididas.
    """
    configured = str(getattr(settings, 'FFMPEG_BINARY', '') or '').strip()
    if configured:
        return configured

    system_path = shutil.which('ffmpeg')
    if system_path:
        return system_path

    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        return bundled if bundled else None
    except Exception:
        return None


def _ffprobe_binary() -> str | None:
    configured = str(getattr(settings, 'FFPROBE_BINARY', '') or '').strip()
    if configured:
        return configured
    return shutil.which('ffprobe')


def _media_duration_seconds(path: Path) -> float | None:
    ffprobe = _ffprobe_binary()
    if ffprobe:
        try:
            result = subprocess.run(
                [
                    ffprobe, '-v', 'error', '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=60,
            )
            value = result.stdout.strip()
            return float(value) if value else None
        except Exception:
            pass

    ffmpeg = _ffmpeg_binary()
    if not ffmpeg:
        return None
    try:
        # ffmpeg mostra a duração no stderr quando chamado apenas para inspecionar o arquivo.
        result = subprocess.run(
            [ffmpeg, '-i', str(path), '-f', 'null', '-'],
            capture_output=True,
            text=True,
            timeout=90,
        )
        combined = f'{result.stdout}\n{result.stderr}'
        match = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', combined)
        if not match:
            return None
        hours, minutes, seconds = match.groups()
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except Exception:
        return None


def _transcribe_in_chunks(*, source_path: Path, temp_dir: Path, duration: float | None, chunk_seconds: int, overlap_seconds: int) -> str:
    if duration is None:
        duration = _media_duration_seconds(source_path)
    if not duration:
        # Sem duração, faz uma conversão única comprimida e envia direto.
        converted = temp_dir / 'audio_convertido.flac'
        _convert_audio_slice(source_path, converted, start=None, duration=None)
        return _transcribe_file_path(converted).strip()

    chunk_paths = _split_media_precisely(
        source_path=source_path,
        temp_dir=temp_dir,
        duration=duration,
        chunk_seconds=chunk_seconds,
        overlap_seconds=overlap_seconds,
    )
    if not chunk_paths:
        return _transcribe_file_path(source_path).strip()

    parts: list[str] = []
    total = len(chunk_paths)
    for index, chunk_path in enumerate(chunk_paths, start=1):
        chunk_text = _transcribe_file_path(chunk_path).strip()
        if chunk_text:
            start_second = _chunk_start_second(index, chunk_seconds, overlap_seconds)
            parts.append(f'[Parte {index}/{total} — aprox. {math.floor(start_second / 60)} min]\n{chunk_text}')

    joined = '\n\n'.join(parts).strip()
    if not joined:
        raise RuntimeError('A transcrição por partes não retornou texto.')
    return joined


def _split_media_precisely(*, source_path: Path, temp_dir: Path, duration: float, chunk_seconds: int, overlap_seconds: int) -> list[Path]:
    chunk_dir = temp_dir / 'chunks'
    chunk_dir.mkdir(parents=True, exist_ok=True)

    stride = max(10, chunk_seconds - overlap_seconds)
    starts: list[float] = []
    current = 0.0
    while current < duration:
        starts.append(current)
        current += stride

    paths: list[Path] = []
    for index, start in enumerate(starts, start=1):
        remaining = max(0.0, duration - start)
        length = min(chunk_seconds, remaining)
        if length < 3:
            continue
        output_path = chunk_dir / f'parte_{index:04d}.flac'
        _convert_audio_slice(source_path, output_path, start=start, duration=length)
        if output_path.exists() and output_path.stat().st_size > 1024:
            paths.append(output_path)
    return paths


def _chunk_start_second(index: int, chunk_seconds: int, overlap_seconds: int) -> int:
    stride = max(10, chunk_seconds - overlap_seconds)
    return max(0, (index - 1) * stride)


def _convert_audio_slice(source_path: Path, output_path: Path, *, start: float | None, duration: float | None) -> None:
    ffmpeg = _ffmpeg_binary()
    if not ffmpeg:
        raise RuntimeError('ffmpeg não está disponível no servidor para dividir/converter o áudio.')
    command = [ffmpeg, '-y']
    if start is not None:
        command.extend(['-ss', f'{start:.3f}'])
    command.extend(['-i', str(source_path)])
    if duration is not None:
        command.extend(['-t', f'{duration:.3f}'])
    command.extend([
        '-map', '0:a:0', '-vn', '-sn', '-dn',
        '-ac', '1', '-ar', '16000',
        '-compression_level', '8',
        str(output_path),
    ])
    subprocess.run(command, check=True, capture_output=True, text=True, timeout=None)


def _looks_incomplete(text: str, duration_seconds: float) -> bool:
    """Heurística conservadora para detectar transcrição curta demais."""
    stripped = (text or '').strip()
    if duration_seconds < 90:
        return False
    # Em aulas faladas, menos de ~120 caracteres por minuto costuma indicar corte.
    min_chars = int((duration_seconds / 60) * 120)
    return len(stripped) < min_chars


def _transcribe_file_path(path: Path) -> str:
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'groq':
        return _transcribe_path_with_groq(path)
    return _transcribe_path_with_openai(path)


def _transcribe_path_with_openai(path: Path) -> str:
    api_key = getattr(settings, 'OPENAI_API_KEY', '').strip()
    return _transcribe_path_via_http(
        path=path,
        api_key=api_key,
        base_url='https://api.openai.com/v1',
        model=getattr(settings, 'OPENAI_TRANSCRIPTION_MODEL', 'whisper-1'),
    )


def _transcribe_path_with_groq(path: Path) -> str:
    api_key = (getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')).strip()
    return _transcribe_path_via_http(
        path=path,
        api_key=api_key,
        base_url='https://api.groq.com/openai/v1',
        model=getattr(settings, 'GROQ_TRANSCRIPTION_MODEL', 'whisper-large-v3'),
    )


def _transcribe_path_via_http(*, path: Path, api_key: str, base_url: str, model: str) -> str:
    if not api_key:
        raise RuntimeError('Chave de transcrição ausente. Configure GROQ_API_KEY ou OPENAI_API_KEY.')

    with path.open('rb') as file_obj:
        response = requests.post(
            f'{base_url}/audio/transcriptions',
            headers={'Authorization': f'Bearer {api_key}'},
            data={
                'model': model,
                'response_format': 'text',
                'language': getattr(settings, 'TRANSCRIPTION_LANGUAGE', 'pt') or 'pt',
                'temperature': '0',
            },
            files={'file': (path.name, file_obj, 'application/octet-stream')},
            timeout=600,
        )

    if response.status_code >= 400:
        raise RuntimeError(f'API de transcrição retornou HTTP {response.status_code}: {response.text[:800]}')

    content_type = response.headers.get('content-type', '').lower()
    if 'application/json' in content_type:
        data = response.json()
        text = data.get('text') or data.get('transcript') or ''
    else:
        text = response.text or ''

    text = text.strip()
    if not text:
        raise RuntimeError('A API de transcrição retornou texto vazio.')
    return text


def _fallback_transcription(*, title: str, subject: str, area: str, error: str = '') -> str:
    extra = f'\n\nObservação técnica: a tentativa de transcrição por IA retornou: {error}' if error else ''
    return f"""# Transcrição demonstrativa — {title}

Modo local ativo: nenhuma chave OPENAI_API_KEY/GROQ_API_KEY foi configurada no arquivo .env, ou a transcrição externa não pôde ser concluída.

Para transcrever uma aula completa em áudio/vídeo, configure uma chave de IA no .env. Para aulas longas, instale também o ffmpeg no Mac com: brew install ffmpeg.

## Aula
- **Título:** {title}
- **Matéria:** {subject or 'não informada'}
- **Área:** {area}

## Texto transcrito do professor
Professor: Hoje nós vamos trabalhar o tema da aula e entender os conceitos centrais passo a passo. Primeiro, observem que não basta decorar a definição: é preciso compreender a lógica do assunto e como ele aparece em situações práticas.

Professor: Em seguida, vamos organizar o conteúdo em blocos. No primeiro bloco, identificamos o conceito principal. No segundo, relacionamos esse conceito com exemplos. No terceiro, analisamos os pontos que costumam ser cobrados em prova.

Professor: Guardem esta ideia: quando vocês forem revisar, tentem explicar o tema com as próprias palavras. Depois, transformem os trechos mais importantes em perguntas. Esse processo melhora a memorização e ajuda a perceber lacunas de compreensão.

Professor: Para finalizar, revisem a aula pela transcrição completa, façam um resumo separado e resolvam questões relacionadas ao assunto. A transcrição é o registro da fala; o resumo é apenas um material de apoio criado depois.
{extra}
"""
