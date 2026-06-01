"""Camada de IA do ACADEME.IA.

A aplicação funciona em dois modos:
1. OpenAI configurado no .env: usa API real.
2. Sem chave: usa fallback local estruturado para permitir uso e demonstração imediata.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

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


def _call_openai(system_prompt: str, user_prompt: str) -> str | None:
    """Chama o provedor configurado.

    O nome foi mantido para compatibilidade interna, mas a função agora aceita
    OpenAI e GroqCloud por meio do cliente OpenAI-compatible.
    """
    if not has_configured_ai():
        return None
    try:
        from openai import OpenAI

        provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
        if provider == 'groq':
            api_key = (getattr(settings, 'GROQ_API_KEY', '') or getattr(settings, 'OPENAI_API_KEY', '')).strip()
            client = OpenAI(api_key=api_key, base_url='https://api.groq.com/openai/v1')
            model = getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant')
        else:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')

        response = client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
            temperature=0.35,
        )
        return response.choices[0].message.content or ''
    except Exception as exc:
        return f'[[IA indisponível em {_provider_label()}: {exc}]]\n\n{_fallback_notice()}'


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
    system_prompt = _base_system_prompt(area)
    user_prompt = f"""
Crie um resumo em português para ACADEME.IA.
Área: {_area_label(area)}
Título/assunto: {title}
Matéria: {subject or 'não informada'}
Tipo de resumo: {summary_type}
Nível: {level}
Conteúdo base:
{input_text or title}

A saída deve conter título, introdução, tópicos principais, explicação detalhada, exemplos, pontos que caem em prova e conclusão.
""".strip()
    ai_result = _call_openai(system_prompt, user_prompt)
    if ai_result and not _is_error_result(ai_result):
        return ai_result

    fallback = _fallback_summary(area, title, subject, input_text, summary_type, level)
    if _is_error_result(ai_result):
        return fallback + '\n\n## Observação técnica\n' + ai_result
    return fallback


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
