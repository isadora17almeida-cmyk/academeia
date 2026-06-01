from __future__ import annotations

from datetime import timedelta
from django.utils import timezone


def _area_focus(area: str) -> str:
    if area == 'direito':
        return 'lei seca, doutrina resumida, jurisprudência essencial, questões comentadas e casos práticos'
    if area == 'medicina':
        return 'anatomia/fisiologia, fisiopatologia, diagnóstico, conduta, questões e casos clínicos'
    return 'conceitos, exemplos, exercícios, revisão ativa e simulados'


def build_local_study_plan(*, area: str, course: str, subjects: str, exam_date, daily_minutes: int, difficulty: str, objective: str) -> str:
    subject_list = [s.strip() for s in subjects.replace(',', '\n').split('\n') if s.strip()]
    if not subject_list:
        subject_list = ['Revisão geral']
    start = timezone.localdate()
    if exam_date and exam_date > start:
        total_days = max((exam_date - start).days, 7)
    else:
        total_days = 14
    days = min(max(total_days, 7), 60)
    focus = _area_focus(area)
    blocks = []
    for i in range(days):
        date = start + timedelta(days=i)
        subject = subject_list[i % len(subject_list)]
        if i % 7 == 6:
            activity = f'Simulado curto + correção ativa de erros em {subject}.'
        elif i % 3 == 2:
            activity = f'Revisão espaçada + flashcards + 10 questões sobre {subject}.'
        else:
            activity = f'Estudo teórico de {subject}: {focus}.'
        blocks.append(f'- **Dia {i + 1} — {date:%d/%m/%Y}:** {activity} Tempo sugerido: {daily_minutes} min.')
    return f"""# Plano de estudos — {course or 'ACADEME.IA'}

**Objetivo:** {objective}  
**Dificuldade percebida:** {difficulty}  
**Tempo diário:** {daily_minutes} minutos  
**Área:** {area}

## Estratégia geral
1. Estude em ciclos curtos com revisão ativa.
2. Faça questões desde o primeiro dia.
3. Transforme erros em flashcards.
4. Reserve um bloco semanal para simulado e correção.
5. Antes da prova, priorize pontos fracos e temas recorrentes.

## Cronograma diário
{chr(10).join(blocks)}

## Metas semanais
- Concluir pelo menos 5 blocos de estudo.
- Gerar 20 flashcards dos pontos mais difíceis.
- Fazer um simulado ou lista de questões.
- Revisar erros e atualizar a biblioteca.

## Progresso sugerido
Marque cada bloco concluído. Meta ideal: 80% ou mais de execução semanal.
"""
