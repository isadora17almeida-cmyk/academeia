"""Camada central de IA do ACADEME.IA.

Esta versão usa HTTP direto para OpenAI/Groq, gera questões discursivas,
resumos avançados longos por blocos e flashcards no estilo Anki.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import requests
from django.conf import settings


@dataclass
class AIContext:
    area: str = 'geral'
    subject: str = ''
    level: str = 'intermediario'
    difficulty: str = 'media'


def _area_label(area: str) -> str:
    labels = {
        'direito': 'Direito', 'medicina': 'Medicina', 'enfermagem': 'Enfermagem',
        'psicologia': 'Psicologia', 'administracao': 'Administração', 'engenharia': 'Engenharia',
        'pedagogia': 'Pedagogia', 'contabilidade': 'Contabilidade', 'geral': 'Geral', 'outros': 'Outros'
    }
    return labels.get(area, 'Geral')


def _difficulty_label(difficulty: str) -> str:
    return {'facil': 'fácil', 'media': 'média', 'dificil': 'difícil'}.get(difficulty, difficulty)


def has_configured_ai() -> bool:
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'groq':
        return bool((getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')).strip())
    return bool(getattr(settings, 'OPENAI_API_KEY', '').strip())


def _provider_label() -> str:
    return 'GroqCloud' if getattr(settings, 'AI_PROVIDER', 'openai').lower() == 'groq' else 'OpenAI'


def _is_error_result(text: str | None) -> bool:
    return bool(text and text.startswith('[[IA indisponível'))


def _fallback_notice() -> str:
    return 'Configure GROQ_API_KEY ou OPENAI_API_KEY nas variáveis de ambiente para usar IA real.'


def _call_openai(system_prompt: str, user_prompt: str, *, max_tokens: int | None = None, temperature: float = 0.25) -> str | None:
    if not has_configured_ai():
        return None
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'groq':
        api_key = (getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')).strip()
        base_url = 'https://api.groq.com/openai/v1'
        model = getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant')
    else:
        api_key = getattr(settings, 'OPENAI_API_KEY', '').strip()
        base_url = 'https://api.openai.com/v1'
        model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
    payload: dict[str, Any] = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': temperature,
    }
    if max_tokens:
        payload['max_tokens'] = int(max_tokens)
    try:
        response = requests.post(
            f'{base_url}/chat/completions',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json=payload,
            timeout=(30, 240),
        )
        if response.status_code >= 400:
            return f'[[IA indisponível em {_provider_label()}: HTTP {response.status_code} - {response.text[:600]}]]'
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', '') or ''
    except Exception as exc:
        return f'[[IA indisponível em {_provider_label()}: {exc}]]'


def _base_system_prompt(area: str) -> str:
    if area == 'direito':
        return (
            'Você é um professor de Direito no Brasil. Produza materiais para OAB, concursos e provas. '
            'Use linguagem didática, estrutura jurídica, conceitos, requisitos, efeitos, exceções, exemplos práticos e pontos de prova. '
            'Não invente lei ou artigo; quando não houver base no texto, indique que não foi mencionado.'
        )
    if area == 'medicina':
        return (
            'Você é um professor de Medicina. Explique conceitos, fisiologia, fisiopatologia, clínica, diagnóstico, conduta, exemplos e pontos de prova. '
            'O conteúdo é educacional e não substitui orientação profissional.'
        )
    return 'Você é um tutor acadêmico. Transforme aulas, PDFs e materiais em conteúdo de estudo claro, completo e organizado.'


def generate_summary(*, area: str, title: str, subject: str, input_text: str, summary_type: str, level: str) -> str:
    """Gera resumo explicativo. Para aulas longas, resume em partes e consolida."""
    base_text = _normalize_text(input_text or title)
    if not base_text:
        base_text = title
    advanced = level == 'avancado' or summary_type in {'completo', 'prova'}
    chunk_chars = int(getattr(settings, 'SUMMARY_CHUNK_CHARS', 6500))
    max_output = int(getattr(settings, 'SUMMARY_MAX_OUTPUT_TOKENS', 2200 if advanced else 1200))
    chunks = _chunk_text(base_text, chunk_chars)

    system_prompt = _base_system_prompt(area)
    if len(chunks) > 1 and has_configured_ai():
        partials: list[str] = []
        for idx, chunk in enumerate(chunks[:10], start=1):
            partial_prompt = f"""
Faça um resumo parcial fiel do bloco {idx}/{len(chunks)} da aula/material abaixo.
Preserve exemplos citados pelo professor/orientador e explique cada exemplo.
Não invente conteúdo que não esteja no bloco.

Área: {_area_label(area)}
Matéria: {subject or 'não informada'}
Título: {title}

Bloco:
{chunk}

Formato:
## Bloco {idx}
### Ideias explicadas
### Exemplos citados e explicados
### Pontos para prova
""".strip()
            partial = _call_openai(system_prompt, partial_prompt, max_tokens=1100)
            if partial and not _is_error_result(partial):
                partials.append(partial)
            else:
                partials.append(_local_block_summary(chunk, idx))
        source_for_final = '\n\n'.join(partials)
    else:
        source_for_final = base_text[:18000]

    user_prompt = _summary_prompt(
        area=area,
        title=title,
        subject=subject,
        summary_type=summary_type,
        level=level,
        source_text=source_for_final,
        advanced=advanced,
    )
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=max_output)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    return _extractive_summary(area=area, title=title, subject=subject, input_text=base_text, advanced=advanced, ai_error=ai_result or '')


def _summary_prompt(*, area: str, title: str, subject: str, summary_type: str, level: str, source_text: str, advanced: bool) -> str:
    if advanced:
        return f"""
Gere um RESUMO AVANÇADO, explicativo e didático a partir do conteúdo fornecido.
Não faça resumo superficial. Use o conteúdo como material de estudo para prova.
Preserve os exemplos citados pelo professor/orientador e explique cada exemplo de forma clara para o aluno entender.
Quando o tema for de Direito, inclua fundamento jurídico apenas quando estiver no texto ou quando for uma referência segura e genérica.
Não invente falas, dados, exemplos ou leis que não estejam no material.

Área: {_area_label(area)}
Matéria: {subject or 'não informada'}
Título: {title}
Tipo: {summary_type}
Nível: {level}

Conteúdo base:
{source_text}

Estrutura obrigatória:
# Resumo avançado da aula — {title}
## 1. Introdução ao tema
## 2. Conceito central
## 3. Explicação passo a passo
## 4. Fundamentos e base teórica
## 5. Exemplos dados pelo professor/orientador
Para cada exemplo: descreva o exemplo e depois explique o raciocínio.
## 6. Exemplos práticos complementares
## 7. Diferenças importantes
## 8. Pontos cobrados em prova
## 9. Pegadinhas comuns
## 10. Quadro comparativo textual
## 11. Checklist de revisão
## 12. Questões possíveis sobre o tema
## 13. Conclusão
""".strip()
    return f"""
Gere um resumo claro e fiel a partir do conteúdo abaixo.
Preserve os exemplos importantes e não invente conteúdo.

Área: {_area_label(area)}
Matéria: {subject or 'não informada'}
Título: {title}
Conteúdo:
{source_text}

Formato:
# {title}
## Síntese
## Pontos principais
## Exemplos
## Para revisar
## Conclusão
""".strip()


def _normalize_text(text: str) -> str:
    text = re.sub(r'\r\n?', '\n', text or '')
    text = re.sub(r'\[Parte\s+\d+/\d+(?:\s+—[^\]]*)?\]\s*', '', text, flags=re.I)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _chunk_text(text: str, chunk_chars: int) -> list[str]:
    text = _normalize_text(text)
    if len(text) <= chunk_chars:
        return [text]
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    size = 0
    for paragraph in paragraphs or _split_sentences(text):
        if size + len(paragraph) > chunk_chars and current:
            chunks.append('\n\n'.join(current))
            current, size = [], 0
        current.append(paragraph)
        size += len(paragraph) + 2
    if current:
        chunks.append('\n\n'.join(current))
    return chunks or [text[:chunk_chars]]


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text or '') if s.strip()]


def _local_block_summary(chunk: str, idx: int) -> str:
    sentences = _split_sentences(chunk)
    selected = sentences[:4] + sentences[max(4, len(sentences)//2):max(4, len(sentences)//2)+3] + sentences[-3:]
    selected = [s for s in selected if s]
    examples = [s for s in sentences if re.search(r'\b(exemplo|por exemplo|imagine|caso|situação)\b', s, re.I)][:4]
    return f"## Bloco {idx}\n### Ideias explicadas\n" + '\n'.join(f'- {s}' for s in selected[:8]) + "\n\n### Exemplos citados e explicados\n" + ('\n'.join(f'- {s}' for s in examples) or '- Não identificado neste bloco.')


def _extractive_summary(*, area: str, title: str, subject: str, input_text: str, advanced: bool, ai_error: str = '') -> str:
    cleaned = _normalize_text(input_text)
    sentences = _split_sentences(cleaned)
    if not sentences:
        return f"# {title}\n\nNão foi possível gerar resumo porque não há conteúdo base suficiente. {_fallback_notice()}"
    selected = _rank_sentences(sentences, limit=28 if advanced else 14)
    examples = [s for s in sentences if re.search(r'\b(exemplo|por exemplo|imagine|caso|situação|vamos supor)\b', s, re.I)][:8]
    important = [s for s in sentences if re.search(r'\b(importante|prova|atenção|guardem|observem|cuidado|sempre|nunca)\b', s, re.I)][:8]
    terms = _extract_key_terms(cleaned, 18)
    note = ''
    if ai_error:
        note = f"\n> Observação técnica: a IA externa não concluiu o resumo. Foi gerado um resumo local com base no conteúdo real. Detalhe: {ai_error[:240]}\n"
    if advanced:
        return f"""# Resumo avançado da aula — {title}
{note}
## 1. Introdução ao tema
A aula/material trata de **{subject or title}** na área de {_area_label(area)}. O conteúdo abaixo foi organizado a partir da transcrição/PDF enviado, preservando os trechos mais representativos.

## 2. Conceitos e pontos centrais
{_bullets(selected[:10])}

## 3. Explicação passo a passo
{_bullets(selected[10:20])}

## 4. Exemplos dados pelo professor/orientador
{_bullets(examples) if examples else '- Nenhum exemplo explícito foi identificado. Revise a transcrição para confirmar exemplos citados oralmente.'}

## 5. Pontos importantes para prova
{_bullets(important) if important else '- Não foram identificados marcadores explícitos de prova, mas os conceitos centrais devem ser revisados.'}

## 6. Termos-chave
{_bullets(terms)}

## 7. Checklist de revisão
- Consigo explicar o conceito principal sem olhar o material?
- Consigo reproduzir os exemplos da aula e explicar o raciocínio por trás deles?
- Sei diferenciar o tema de institutos parecidos?
- Transformei os pontos principais em questões e flashcards?

## 8. Conclusão
Use este resumo junto com a transcrição completa. Para fixar, resolva questões online no site e revise os flashcards gerados a partir deste conteúdo.
""".strip()
    return f"# {title}\n{note}\n## Síntese\n{_bullets(selected[:8])}\n\n## Exemplos\n{_bullets(examples[:4]) if examples else '- Não mencionado.'}\n\n## Conclusão\nRevise os pontos acima junto com o material original."


def _bullets(items: list[str]) -> str:
    return '\n'.join(f'- {item}' for item in items if item) or '- Não mencionado.'


def _rank_sentences(sentences: list[str], limit: int) -> list[str]:
    stop = _stopwords_pt()
    freq: dict[str, int] = {}
    for s in sentences:
        for w in re.findall(r'[A-Za-zÀ-ÿ]{4,}', s.lower()):
            if w not in stop:
                freq[w] = freq.get(w, 0) + 1
    scored: list[tuple[float, int, str]] = []
    total = max(1, len(sentences))
    for idx, s in enumerate(sentences):
        score = sum(freq.get(w, 0) for w in re.findall(r'[A-Za-zÀ-ÿ]{4,}', s.lower()) if w not in stop)
        if re.search(r'\b(exemplo|prova|artigo|lei|código|conceito|importante|observem)\b', s, re.I):
            score += 8
        # Garante cobertura de início, meio e fim.
        score += 3 * (1 - abs(idx / total - 0.5))
        scored.append((score, idx, s.strip()))
    top = sorted(scored, key=lambda x: x[0], reverse=True)[:limit]
    return [s for _, _, s in sorted(top, key=lambda x: x[1])]


def _extract_key_terms(text: str, limit: int) -> list[str]:
    stop = _stopwords_pt()
    counts: dict[str, int] = {}
    for word in re.findall(r'[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{4,}', text.lower()):
        if word not in stop:
            counts[word] = counts.get(word, 0) + 1
    return [w for w, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:limit]]


def _stopwords_pt() -> set[str]:
    return {'aquele','aquela','aquilo','agora','assim','ainda','apenas','cada','como','comum','contra','depois','dessa','desse','desta','deste','disso','dizer','então','entre','essa','esse','esta','este','falar','fazer','forma','foram','gente','hoje','isso','mais','mesma','mesmo','muito','nossa','nosso','onde','outra','outro','para','parte','pelas','pelos','pode','porque','porém','professor','quando','qual','quais','sobre','também','todas','todos','vamos','você','vocês','será','serão','termos','existe','existem','direito','aula','tema','texto','transcrição','conteúdo'}


def generate_questions(*, area: str, subject: str, quantity: int, difficulty: str, question_type: str, include_answer: bool, include_explanation: bool, source_text: str = '') -> list[dict[str, Any]]:
    system_prompt = _base_system_prompt(area)
    base = _normalize_text(source_text)[:12000]
    if question_type == 'discursiva':
        schema = '[{"statement":"enunciado contextualizado com comando completo","alternatives":[],"correct_answer":"resposta modelo completa","explanation":"comentário explicativo + critérios de correção","difficulty":"%s","subject":"%s"}]' % (difficulty, subject)
        special = 'As questões discursivas devem conter contexto, comando, resposta modelo, critérios de correção e comentário didático.'
    else:
        schema = '[{"statement":"enunciado","alternatives":["A) ...","B) ...","C) ...","D) ...","E) ..."],"correct_answer":"A","explanation":"gabarito comentado","difficulty":"%s","subject":"%s"}]' % (difficulty, subject)
        special = 'As questões objetivas devem ter alternativas clicáveis e gabarito comentado.'
    user_prompt = f"""
Gere {quantity} questões em português no formato JSON puro, sem markdown.
Área: {_area_label(area)}
Assunto: {subject}
Dificuldade: {_difficulty_label(difficulty)}
Tipo: {question_type}
Incluir gabarito: {include_answer}
Incluir comentário: {include_explanation}
{special}

Material base opcional:
{base or 'Sem material base; use o assunto indicado.'}

Formato exato:
{schema}
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=2400)
    if ai_result and not _is_error_result(ai_result):
        parsed = _safe_json_list(ai_result)
        if parsed:
            return _normalize_questions(parsed[:quantity], difficulty, subject, question_type, include_answer, include_explanation)
    return _fallback_questions(area, subject, quantity, difficulty, question_type, include_answer, include_explanation, source_text=base)


def _safe_json_list(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json|JSON)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception:
        match = re.search(r'\[.*\]', text, flags=re.S)
        if match:
            try:
                data = json.loads(match.group(0))
                if isinstance(data, list):
                    return [item for item in data if isinstance(item, dict)]
            except Exception:
                pass
    return []


def _normalize_questions(items: list[dict[str, Any]], difficulty: str, subject: str, question_type: str, include_answer: bool, include_explanation: bool) -> list[dict[str, Any]]:
    normalized = []
    for item in items:
        alternatives = item.get('alternatives') or []
        if question_type == 'discursiva':
            alternatives = []
        normalized.append({
            'statement': item.get('statement') or item.get('enunciado') or '',
            'alternatives': alternatives,
            'correct_answer': (item.get('correct_answer') or item.get('answer') or item.get('resposta') or '') if include_answer else '',
            'explanation': (item.get('explanation') or item.get('comentario') or item.get('criteria') or '') if include_explanation else '',
            'difficulty': item.get('difficulty') or difficulty,
            'subject': item.get('subject') or subject,
        })
    return normalized


def _fallback_questions(area: str, subject: str, quantity: int, difficulty: str, question_type: str, include_answer: bool, include_explanation: bool, source_text: str = '') -> list[dict[str, Any]]:
    questions = []
    area_label = _area_label(area)
    source_hint = _rank_sentences(_split_sentences(source_text), limit=3) if source_text else []
    for i in range(1, quantity + 1):
        if question_type == 'discursiva':
            statement = f'Explique, de forma fundamentada, o tema "{subject}" considerando conceito, requisitos, efeitos e um exemplo prático. Questão {i}.'
            alternatives = []
            correct = f'Resposta modelo: o aluno deve conceituar {subject}, indicar sua estrutura, apresentar efeitos práticos, diferenciar de institutos próximos e desenvolver exemplo coerente.'
            explanation = 'Critérios de correção: conceito; base teórica; exemplo; aplicação prática; conclusão. ' + (f'Trechos base: {" ".join(source_hint)}' if source_hint else _fallback_notice())
        else:
            statement = f'({area_label}) Sobre {subject}, assinale a alternativa correta. Questão {i}.'
            alternatives = ['A) Conceito, requisitos, efeitos e aplicação prática.', 'B) Apenas memorização literal de termos isolados.', 'C) Exclusivamente dados históricos sem relação com prova.', 'D) Uma resposta genérica sem conexão com o assunto.', 'E) Nenhuma das alternativas anteriores.']
            correct = 'A'
            explanation = f'A alternativa correta organiza o tema em conceito, requisitos, efeitos e aplicação prática. {_fallback_notice()}'
        questions.append({'statement': statement, 'alternatives': alternatives, 'correct_answer': correct if include_answer else '', 'explanation': explanation if include_explanation else '', 'difficulty': difficulty, 'subject': subject})
    return questions


def generate_flashcards(*, area: str, subject: str, quantity: int, difficulty: str, source_text: str = '') -> list[dict[str, Any]]:
    system_prompt = _base_system_prompt(area)
    base = _normalize_text(source_text)[:10000]
    user_prompt = f"""
Gere {quantity} flashcards estilo Anki em JSON puro, sem markdown.
Cada card deve ter frente curta e verso didático, útil para revisão ativa.
Área: {_area_label(area)}
Assunto: {subject}
Dificuldade: {_difficulty_label(difficulty)}
Material base:
{base or 'Sem material base.'}

Formato:
[
  {{"question":"frente do card em forma de pergunta","answer":"verso com resposta objetiva e explicação breve","difficulty":"{difficulty}","subject":"{subject}"}}
]
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=2000)
    if ai_result and not _is_error_result(ai_result):
        parsed = _safe_json_list(ai_result)
        if parsed:
            return parsed[:quantity]
    sentences = _rank_sentences(_split_sentences(base), limit=quantity) if base else []
    cards = []
    for i in range(1, quantity + 1):
        basis = sentences[i-1] if i-1 < len(sentences) else f'O ponto central de {subject}'
        cards.append({'question': f'O que devo lembrar sobre {subject}? #{i}', 'answer': f'{basis}\n\n{_fallback_notice()}', 'difficulty': difficulty, 'subject': subject})
    return cards


def correct_transcript(text: str, area: str = 'geral') -> str:
    system_prompt = _base_system_prompt(area)
    user_prompt = f'Corrija pontuação e legibilidade desta transcrição sem resumir e sem alterar sentido. Remova marcações técnicas como [Parte X/Y]:\n\n{_normalize_text(text)[:16000]}'
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=2400)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    return _normalize_text(text)


def split_topics(text: str, area: str = 'geral') -> str:
    system_prompt = _base_system_prompt(area)
    user_prompt = f'Separe esta transcrição por tópicos didáticos, com títulos e subtópicos claros, sem inventar conteúdo:\n\n{_normalize_text(text)[:16000]}'
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=2200)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    paragraphs = [p.strip() for p in _normalize_text(text).split('\n') if p.strip()]
    return '\n\n'.join(f'## Tópico {idx}\n{paragraph}' for idx, paragraph in enumerate(paragraphs[:12], start=1)) or _fallback_notice()


def generate_study_plan(*, area: str, course: str, subjects: str, exam_date, daily_minutes: int, difficulty: str, objective: str) -> str:
    system_prompt = _base_system_prompt(area)
    user_prompt = f"""
Crie um plano de estudos personalizado e interativo.
Área: {_area_label(area)}
Curso: {course}
Matérias: {subjects}
Data da prova: {exam_date or 'não informada'}
Tempo por dia: {daily_minutes} minutos
Dificuldade: {_difficulty_label(difficulty)}
Objetivo: {objective}
Inclua cronograma diário, revisão espaçada, simulados, metas semanais, flashcards e indicadores de progresso.
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=2200)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    from .study_plan_service import build_local_study_plan
    return build_local_study_plan(area=area, course=course, subjects=subjects, exam_date=exam_date, daily_minutes=daily_minutes, difficulty=difficulty, objective=objective)
