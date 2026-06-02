"""Camada de IA do ACADEME.IA.

A aplicação funciona em dois modos:
1. OpenAI configurado no .env: usa API real.
2. Sem chave: usa fallback local estruturado para permitir uso e demonstração imediata.
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
    return {'direito': 'Direito', 'medicina': 'Medicina', 'geral': 'Geral'}.get(area, 'Geral')


def _difficulty_label(difficulty: str) -> str:
    return {'facil': 'fácil', 'media': 'média', 'dificil': 'difícil'}.get(difficulty, difficulty)


def has_configured_ai() -> bool:
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    if provider == 'groq':
        return bool((getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')).strip())
    return bool(getattr(settings, 'OPENAI_API_KEY', '').strip())


def _provider_label() -> str:
    provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    return 'GroqCloud' if provider == 'groq' else 'OpenAI'


def _is_error_result(text: str | None) -> bool:
    return bool(text and text.startswith('[[IA indisponível'))


def _call_openai(system_prompt: str, user_prompt: str, *, max_tokens: int | None = None) -> str | None:
    """Chama OpenAI/Groq sem usar o SDK oficial.

    A versão anterior usava ``openai.OpenAI``. Em alguns deploys do Render,
    combinações de versões do OpenAI SDK e httpx geravam o erro
    ``Client.__init__() got an unexpected keyword argument 'proxies'``.
    Aqui usamos HTTP direto para evitar esse problema e garantir que resumo,
    questões e demais materiais usem a IA real configurada.
    """
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

    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': 0.25,
    }
    if max_tokens:
        payload['max_tokens'] = int(max_tokens)
    try:
        response = requests.post(
            f'{base_url}/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=180,
        )
        if response.status_code >= 400:
            return f'[[IA indisponível em {_provider_label()}: HTTP {response.status_code} - {response.text[:600]}]]'
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', '') or ''
    except Exception as exc:
        return f'[[IA indisponível em {_provider_label()}: {exc}]]'


def _fallback_notice() -> str:
    return (
        'Modo local demonstrativo ativo. Configure OPENAI_API_KEY ou GROQ_API_KEY no arquivo .env '
        'para gerar conteúdo com IA externa.'
    )


def _base_system_prompt(area: str) -> str:
    if area == 'direito':
        return (
            'Você é um professor de Direito no Brasil, com foco em concursos, OAB e provas universitárias. '
            'Explique com estrutura jurídica: conceito, fundamento legal, princípios, doutrina resumida, jurisprudência quando aplicável, exemplos, pegadinhas e conclusão. '
            'Não invente artigos específicos se não tiver certeza; sinalize quando for necessário conferir a legislação atualizada.'
        )
    if area == 'medicina':
        return (
            'Você é um professor de Medicina para estudantes de graduação. '
            'Explique com estrutura médica: conceito, anatomia, fisiologia, fisiopatologia, sintomas, diagnóstico, exames, tratamento, caso clínico, pontos de prova e conclusão. '
            'Não substitua orientação médica profissional.'
        )
    return (
        'Você é um tutor acadêmico especializado em transformar conteúdos complexos em materiais de estudo claros, organizados e objetivos.'
    )


def generate_summary(*, area: str, title: str, subject: str, input_text: str, summary_type: str, level: str) -> str:
    """Gera resumo sem estourar o limite de tokens da Groq.

    A versão anterior enviava até 30.000 caracteres de transcrição em uma única
    chamada. Em contas gratuitas/baixo limite da Groq isso pode causar HTTP 413
    por tokens por minuto. Esta versão primeiro condensa a transcrição inteira
    de modo local e só então envia uma entrada curta para a IA.

    Regra importante: se a IA falhar, o sistema não mostra mais o erro bruto como
    "resumo"; ele monta um resumo local fiel usando trechos reais da transcrição.
    """
    system_prompt = _base_system_prompt(area)
    base_text = (input_text or title).strip()
    if not base_text:
        base_text = title

    source_text = _prepare_summary_source(base_text)
    user_prompt = f"""
Crie um resumo fiel em português para ACADEME.IA usando SOMENTE o conteúdo base abaixo.
Não invente falas, exemplos, leis, artigos, autores, jurisprudência ou conceitos que não estejam no conteúdo.
Se o conteúdo for uma transcrição de aula, resuma exatamente o que foi explicado pelo professor.

Área: {_area_label(area)}
Título/assunto: {title}
Matéria: {subject or 'não informada'}
Tipo de resumo: {summary_type}
Nível: {level}

Conteúdo base condensado a partir da transcrição completa:
{source_text}

Formato obrigatório:
# {title}
## Síntese da aula
## Pontos explicados pelo professor
## Conceitos principais
## Exemplos citados na aula
## Pontos de atenção para prova
## Conclusão

Se alguma seção não existir no conteúdo base, escreva: "Não mencionado na aula."
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt, max_tokens=getattr(settings, 'SUMMARY_MAX_OUTPUT_TOKENS', 1200))
    if ai_result and not _is_error_result(ai_result):
        return ai_result

    return _extractive_summary(
        area=area,
        title=title,
        subject=subject,
        input_text=base_text,
        summary_type=summary_type,
        level=level,
        ai_error=ai_result if _is_error_result(ai_result) else '',
    )


def _prepare_summary_source(text: str) -> str:
    """Reduz uma transcrição longa mantendo cobertura do começo, meio e fim.

    O objetivo não é cortar a aula de forma cega; é extrair trechos distribuídos
    por toda a transcrição para caber no limite do modelo usado no Render.
    """
    cleaned = _normalize_transcript_for_summary(text)
    direct_chars = int(getattr(settings, 'SUMMARY_DIRECT_CHARS', 9000))
    max_chars = int(getattr(settings, 'SUMMARY_SOURCE_MAX_CHARS', 9000))
    if len(cleaned) <= direct_chars:
        return cleaned

    parts = _split_transcript_parts(cleaned)
    if not parts:
        return cleaned[:max_chars]

    budget_per_part = max(180, max_chars // max(1, len(parts)))
    selected: list[str] = []
    total = len(parts)
    for idx, part in enumerate(parts, start=1):
        snippet = _smart_excerpt(part, budget_per_part)
        if snippet:
            selected.append(f'[Trecho {idx}/{total}] {snippet}')

    condensed = '\n\n'.join(selected)
    if len(condensed) > max_chars:
        condensed = _evenly_sample_text(condensed, max_chars)
    return condensed.strip()


def _normalize_transcript_for_summary(text: str) -> str:
    text = re.sub(r'\r\n?', '\n', text or '')
    text = re.sub(r'\[Parte\s+\d+/\d+\s+—[^\]]*\]', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def _split_transcript_parts(text: str) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n+', text) if p.strip()]
    if len(paragraphs) >= 6:
        return paragraphs
    sentences = _split_sentences(text)
    if not sentences:
        return [text] if text else []
    grouped = []
    current: list[str] = []
    current_len = 0
    for sentence in sentences:
        current.append(sentence)
        current_len += len(sentence)
        if current_len >= 1200:
            grouped.append(' '.join(current))
            current = []
            current_len = 0
    if current:
        grouped.append(' '.join(current))
    return grouped


def _smart_excerpt(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    sentences = _split_sentences(text)
    if not sentences:
        return text[:max_chars].rsplit(' ', 1)[0]
    chosen: list[str] = []
    used = 0
    # Prioriza início do trecho, mas inclui uma frase do meio/fim se couber.
    candidate_indexes = [0, 1, max(0, len(sentences)//2), max(0, len(sentences)-1)]
    seen = set()
    for idx in candidate_indexes:
        if idx in seen or idx >= len(sentences):
            continue
        seen.add(idx)
        sentence = sentences[idx]
        if used + len(sentence) + 1 <= max_chars:
            chosen.append(sentence)
            used += len(sentence) + 1
    if not chosen:
        return text[:max_chars].rsplit(' ', 1)[0]
    return ' '.join(chosen).strip()


def _evenly_sample_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    if max_chars < 1000:
        return text[:max_chars]
    third = max_chars // 3
    middle_start = max(0, len(text)//2 - third//2)
    return '\n\n'.join([
        text[:third].rsplit(' ', 1)[0],
        text[middle_start:middle_start+third].strip().rsplit(' ', 1)[0],
        text[-third:].strip(),
    ])


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r'(?<=[.!?])\s+', text or '') if s.strip()]


def _extractive_summary(*, area: str, title: str, subject: str, input_text: str, summary_type: str, level: str, ai_error: str = '') -> str:
    """Resumo local fiel quando a IA ultrapassa limite ou fica indisponível."""
    cleaned = _normalize_transcript_for_summary(input_text)
    sentences = _split_sentences(cleaned)
    if not sentences:
        return _fallback_summary(area, title, subject, input_text, summary_type, level)

    selected = _rank_representative_sentences(sentences, limit=14)
    key_terms = _extract_key_terms(cleaned, limit=16)
    examples = [s for s in selected if re.search(r'\b(exemplo|por exemplo|imagine|caso|situação)\b', s, flags=re.IGNORECASE)]
    attention = [s for s in selected if re.search(r'\b(prova|atenção|cuidado|importante|observem|guardem|não basta|sempre|nunca)\b', s, flags=re.IGNORECASE)]

    error_note = ''
    if ai_error:
        compact_error = ai_error.replace('\n', ' ')[:350]
        error_note = f'\n\n> Observação: a IA externa não foi usada no resumo final porque retornou limite/erro técnico. O resumo abaixo foi montado localmente com trechos reais da transcrição. Detalhe: {compact_error}\n'

    bullets = '\n'.join(f'- {s}' for s in selected[:8]) or '- Não mencionado na aula.'
    concept_bullets = '\n'.join(f'- {term}' for term in key_terms) or '- Não mencionado na aula.'
    example_bullets = '\n'.join(f'- {s}' for s in examples[:4]) or '- Não mencionado na aula.'
    attention_bullets = '\n'.join(f'- {s}' for s in attention[:5]) or '- Não mencionado na aula.'

    return f"""# {title}
{error_note}
## Síntese da aula
A aula tratou de **{subject or title}** na área de {_area_label(area)}. O conteúdo abaixo foi produzido a partir da transcrição do professor, sem acrescentar informações externas.

## Pontos explicados pelo professor
{bullets}

## Conceitos principais
{concept_bullets}

## Exemplos citados na aula
{example_bullets}

## Pontos de atenção para prova
{attention_bullets}

## Conclusão
Revise a transcrição completa junto com estes pontos. Para prova, transforme cada item explicado pelo professor em uma pergunta ativa e compare com os exemplos mencionados na aula.
""".strip()


def _rank_representative_sentences(sentences: list[str], limit: int = 12) -> list[str]:
    stopwords = _stopwords_pt()
    frequencies: dict[str, int] = {}
    for sentence in sentences:
        for word in re.findall(r'[A-Za-zÀ-ÿ]{4,}', sentence.lower()):
            if word not in stopwords:
                frequencies[word] = frequencies.get(word, 0) + 1
    scored: list[tuple[float, int, str]] = []
    total = max(1, len(sentences))
    for idx, sentence in enumerate(sentences):
        words = re.findall(r'[A-Za-zÀ-ÿ]{4,}', sentence.lower())
        score = sum(frequencies.get(w, 0) for w in words if w not in stopwords)
        if re.search(r'\b(professor|observem|guardem|importante|prova|exemplo|artigo|código|lei)\b', sentence, re.I):
            score += 8
        # Distribui a seleção pela aula inteira: começo, meio e final têm chance.
        position_bonus = 1.0 - abs((idx / total) - 0.5) * 0.15
        scored.append((score * position_bonus, idx, sentence.strip()))
    top = sorted(scored, key=lambda item: item[0], reverse=True)[:limit]
    return [sentence for _, _, sentence in sorted(top, key=lambda item: item[1])]


def _extract_key_terms(text: str, limit: int = 12) -> list[str]:
    stopwords = _stopwords_pt()
    counts: dict[str, int] = {}
    for raw in re.findall(r'[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ\-]{4,}', text.lower()):
        word = raw.strip('-')
        if word and word not in stopwords:
            counts[word] = counts.get(word, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ordered[:limit]]


def _stopwords_pt() -> set[str]:
    return {
        'aquele', 'aquela', 'aquilo', 'agora', 'assim', 'ainda', 'apenas', 'cada', 'como', 'comum', 'contra',
        'depois', 'dessa', 'desse', 'desta', 'deste', 'disso', 'dizer', 'então', 'entre', 'essa', 'esse', 'esta',
        'este', 'falar', 'fazer', 'forma', 'foram', 'gente', 'hoje', 'isso', 'mais', 'mesma', 'mesmo', 'muito',
        'nossa', 'nosso', 'onde', 'outra', 'outro', 'para', 'parte', 'pelas', 'pelos', 'pode', 'porque', 'porém',
        'professor', 'quando', 'qual', 'quais', 'sobre', 'também', 'todas', 'todos', 'vamos', 'você', 'vocês',
        'será', 'serão', 'termos', 'existe', 'existem', 'direito', 'aula', 'tema', 'texto', 'transcrição'
    }

def _fallback_summary(area: str, title: str, subject: str, input_text: str, summary_type: str, level: str) -> str:
    base = input_text.strip() or title
    if area == 'direito':
        return f"""# {title}

**Área:** Direito  
**Matéria:** {subject or 'Geral'}  
**Tipo:** {summary_type}  
**Nível:** {level}

## Introdução
{_fallback_notice()} Este material organiza o tema **{title}** para revisão jurídica objetiva e uso em provas.

## Conceito
O tema deve ser compreendido a partir de sua função prática dentro do sistema jurídico. Em termos de estudo, identifique a definição central, os sujeitos envolvidos, os efeitos jurídicos e as consequências do descumprimento.

## Fundamento legal
Consulte sempre a legislação atualizada. Para temas de Direito Civil, verifique o Código Civil; para processo, verifique o CPC/CPP; para constitucional, parta da Constituição Federal. Evite decorar artigos isolados sem entender a lógica normativa.

## Princípios relacionados
- Boa-fé objetiva e função social, quando o tema envolver relações privadas.
- Legalidade, proporcionalidade e devido processo legal, quando o tema envolver atuação estatal ou processo.
- Segurança jurídica e proteção da confiança, quando houver efeitos sobre situações consolidadas.

## Doutrina resumida
A doutrina costuma cobrar a diferença entre conceito, natureza jurídica, requisitos, efeitos e exceções. Para prova, monte quadros comparativos e destaque termos técnicos.

## Jurisprudência resumida
Quando aplicável, pesquise entendimento atualizado dos tribunais superiores. Em questões, observe palavras como “sempre”, “nunca”, “exclusivamente” e “necessariamente”, pois frequentemente indicam alternativas erradas.

## Exemplo prático
Imagine uma situação em que uma parte assume determinada obrigação ou conduta prevista em lei ou contrato. A análise deve responder: quem deve agir, qual é a conduta exigida, qual é o prazo, qual é a consequência do inadimplemento e qual medida processual pode ser usada.

## Pegadinhas de prova
- Confundir requisito com efeito.
- Ignorar exceções legais.
- Aplicar regra geral sem verificar norma especial.
- Confundir obrigação, responsabilidade e sanção.

## Questões comentadas
1. **Pergunta:** Qual é o núcleo do tema {title}?  
   **Resposta:** Identificar conceito, base legal, requisitos e efeitos.  
   **Comentário:** A banca costuma exigir domínio da estrutura, não apenas memorização.

## Conclusão
Para dominar **{title}**, revise conceito, fundamento legal, exemplos práticos e exceções. Use casos concretos para transformar o conteúdo em raciocínio jurídico aplicável.

## Conteúdo base analisado
{base[:2000]}
"""
    if area == 'medicina':
        return f"""# {title}

**Área:** Medicina  
**Matéria:** {subject or 'Geral'}  
**Tipo:** {summary_type}  
**Nível:** {level}

## Introdução
{_fallback_notice()} Este resumo organiza **{title}** em estrutura médica para revisão acadêmica.

## Conceito
O tema deve ser compreendido pela definição, função biológica, relação anatômica/fisiológica e relevância clínica.

## Anatomia e fisiologia
- Localize a estrutura ou sistema envolvido.
- Identifique vascularização, inervação e relações anatômicas quando aplicável.
- Relacione função normal com alterações patológicas.

## Fisiopatologia
A fisiopatologia explica como a alteração da função normal gera sinais, sintomas e consequências clínicas. Em prova, foque na sequência causal.

## Sintomas e sinais
Liste manifestações típicas, manifestações de gravidade e achados que ajudam no diagnóstico diferencial.

## Diagnóstico e exames
Associe hipótese clínica a exames complementares. Evite decorar exames isoladamente; entenda por que eles confirmam ou afastam diagnósticos.

## Tratamento
Organize em medidas gerais, conduta inicial, tratamento específico e acompanhamento. Este conteúdo é educacional e não substitui orientação profissional.

## Caso clínico
Paciente apresenta manifestações compatíveis com o tema **{title}**. A resolução exige reconhecer o padrão clínico, levantar hipóteses, pedir exames adequados e propor conduta coerente.

## Pontos importantes para prova
- Relação entre estrutura e função.
- Mecanismo fisiopatológico.
- Diagnóstico diferencial.
- Conduta inicial em cenários frequentes.

## Conclusão
Estude **{title}** integrando anatomia, fisiologia, fisiopatologia e clínica. Essa integração melhora retenção e desempenho em questões.

## Conteúdo base analisado
{base[:2000]}
"""
    return f"""# {title}

**Área:** Geral  
**Matéria:** {subject or 'Geral'}  
**Tipo:** {summary_type}  
**Nível:** {level}

## Introdução
{_fallback_notice()} Este resumo transforma o tema **{title}** em uma revisão organizada.

## Tópicos principais
- Definição do tema.
- Ideias centrais.
- Exemplos práticos.
- Pontos de atenção para prova.
- Conclusão e revisão rápida.

## Explicação detalhada
Comece entendendo o conceito central, depois relacione causas, consequências e aplicações. Uma boa revisão deve responder: o que é, por que importa, como funciona e como costuma ser cobrado.

## Exemplos
Use situações concretas para fixar o conteúdo e criar memória contextual.

## Pontos que caem em prova
- Diferenças conceituais.
- Exceções.
- Aplicações práticas.
- Termos técnicos.

## Conclusão
Revise o tema com perguntas ativas e transforme os tópicos em flashcards para consolidar.

## Conteúdo base analisado
{base[:2000]}
"""


def generate_questions(*, area: str, subject: str, quantity: int, difficulty: str, question_type: str, include_answer: bool, include_explanation: bool) -> list[dict[str, Any]]:
    system_prompt = _base_system_prompt(area)
    user_prompt = f"""
Gere {quantity} questões em português no formato JSON puro, sem markdown.
Área: {_area_label(area)}
Assunto: {subject}
Dificuldade: {_difficulty_label(difficulty)}
Tipo: {question_type}
Incluir gabarito: {include_answer}
Incluir explicação: {include_explanation}

Formato exato:
[
  {{
    "statement": "enunciado",
    "alternatives": ["A) ...", "B) ...", "C) ...", "D) ...", "E) ..."],
    "correct_answer": "A",
    "explanation": "explicação",
    "difficulty": "{difficulty}",
    "subject": "{subject}"
  }}
]
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt)
    if ai_result and not ai_result.startswith('[[IA indisponível'):
        parsed = _safe_json_list(ai_result)
        if parsed:
            return parsed[:quantity]
    return _fallback_questions(area, subject, quantity, difficulty, question_type, include_answer, include_explanation)


def _safe_json_list(text: str) -> list[dict[str, Any]]:
    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        text = text.replace('json\n', '', 1).replace('JSON\n', '', 1)
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception:
        return []
    return []


def _fallback_questions(area: str, subject: str, quantity: int, difficulty: str, question_type: str, include_answer: bool, include_explanation: bool) -> list[dict[str, Any]]:
    questions = []
    area_label = _area_label(area)
    for i in range(1, quantity + 1):
        if question_type == 'multipla':
            alternatives = [
                'A) Conceito, requisitos, efeitos e aplicação prática.',
                'B) Apenas memorização literal de termos isolados.',
                'C) Exclusivamente dados históricos sem relação com prova.',
                'D) Uma resposta genérica sem conexão com o assunto.',
                'E) Nenhuma das alternativas anteriores.',
            ]
            correct = 'A'
        elif question_type == 'vf':
            alternatives = ['Verdadeiro', 'Falso']
            correct = 'Verdadeiro'
        else:
            alternatives = []
            correct = 'Resposta discursiva esperada: apresentar conceito, estrutura, exemplo e conclusão.'
        questions.append({
            'statement': f'({area_label}) Sobre {subject}, assinale ou desenvolva a alternativa que melhor organiza o raciocínio exigido em prova. Questão {i}.',
            'alternatives': alternatives,
            'correct_answer': correct if include_answer else '',
            'explanation': f'{_fallback_notice()} A resposta deve conectar o conceito de {subject} aos critérios centrais da área {area_label}, evitando memorização sem compreensão.' if include_explanation else '',
            'difficulty': difficulty,
            'subject': subject,
        })
    return questions


def generate_flashcards(*, area: str, subject: str, quantity: int, difficulty: str, source_text: str = '') -> list[dict[str, Any]]:
    system_prompt = _base_system_prompt(area)
    user_prompt = f"""
Gere {quantity} flashcards em português no formato JSON puro, sem markdown.
Área: {_area_label(area)}
Assunto: {subject}
Dificuldade: {_difficulty_label(difficulty)}
Texto base: {source_text[:6000]}

Formato:
[
  {{"question": "pergunta", "answer": "resposta", "difficulty": "{difficulty}", "subject": "{subject}"}}
]
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt)
    if ai_result and not ai_result.startswith('[[IA indisponível'):
        parsed = _safe_json_list(ai_result)
        if parsed:
            return parsed[:quantity]
    return [
        {
            'question': f'Qual é o ponto central de {subject}? #{i}',
            'answer': f'O ponto central é compreender conceito, estrutura, exemplos e aplicação em prova. {_fallback_notice()}',
            'difficulty': difficulty,
            'subject': subject,
        }
        for i in range(1, quantity + 1)
    ]


def correct_transcript(text: str, area: str = 'geral') -> str:
    system_prompt = _base_system_prompt(area)
    user_prompt = f'Corrija pontuação, concordância e organização deste texto transcrito sem alterar o sentido:\n\n{text[:12000]}'
    ai_result = _call_openai(system_prompt, user_prompt)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    return f'{_fallback_notice()}\n\nTexto revisado em modo local:\n\n{text.strip()}'


def split_topics(text: str, area: str = 'geral') -> str:
    system_prompt = _base_system_prompt(area)
    user_prompt = f'Separe esta transcrição por tópicos, com títulos e subtópicos claros:\n\n{text[:12000]}'
    ai_result = _call_openai(system_prompt, user_prompt)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    if not paragraphs:
        return _fallback_notice()
    chunks = []
    for idx, paragraph in enumerate(paragraphs[:10], start=1):
        chunks.append(f'## Tópico {idx}\n{paragraph}')
    return f'{_fallback_notice()}\n\n' + '\n\n'.join(chunks)


def generate_study_plan(*, area: str, course: str, subjects: str, exam_date, daily_minutes: int, difficulty: str, objective: str) -> str:
    system_prompt = _base_system_prompt(area)
    user_prompt = f"""
Crie um plano de estudos personalizado.
Área: {_area_label(area)}
Curso: {course}
Matérias: {subjects}
Data da prova: {exam_date or 'não informada'}
Tempo por dia: {daily_minutes} minutos
Dificuldade: {_difficulty_label(difficulty)}
Objetivo: {objective}

Inclua cronograma diário, revisões programadas, simulados, metas semanais e progresso sugerido.
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt)
    if ai_result and not _is_error_result(ai_result):
        return ai_result
    from .study_plan_service import build_local_study_plan
    return build_local_study_plan(area=area, course=course, subjects=subjects, exam_date=exam_date, daily_minutes=daily_minutes, difficulty=difficulty, objective=objective)
