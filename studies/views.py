from __future__ import annotations

from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ExamGenerationForm,
    FlashcardGenerationForm,
    FolderForm,
    LibraryFilterForm,
    QuestionGenerationForm,
    StudyPlanForm,
    SummaryForm,
    TranscriptForm,
)
from .models import Export, Exam, ExamAnswer, Flashcard, Folder, LibraryItem, Question, StudyPlan, Summary, Transcript
from .services.ai_service import (
    correct_transcript,
    generate_flashcards as ai_generate_flashcards,
    generate_questions as ai_generate_questions,
    generate_study_plan,
    generate_summary as ai_generate_summary,
    split_topics,
)
from .services.export_service import export_content
from .services.transcription_service import extract_transcript_only, is_demo_transcription, transcribe_uploaded_file

DIREITO_SUBJECTS = ['Direito Civil', 'Direito Penal', 'Direito Constitucional', 'Processo Civil', 'Processo Penal', 'Direito Administrativo', 'Direito do Trabalho']
MEDICINA_SUBJECTS = ['Anatomia', 'Histologia', 'Fisiologia', 'Patologia', 'Farmacologia', 'Clínica Médica', 'Pediatria', 'Cirurgia']
GERAL_SUBJECTS = ['Resumos', 'Flashcards', 'Simulados', 'Revisão espaçada', 'PDFs', 'Aulas transcritas']


def _extract_transcript_only(text: str) -> str:
    return extract_transcript_only(text)


def _create_library_item(*, user, title, material_type, area, subject='', content='', folder=None, favorite=False, object_id=None):
    return LibraryItem.objects.create(user=user, title=title, material_type=material_type, area=area, subject=subject, content=content, folder=folder, favorite=favorite, object_id=object_id)


def _sync_transcript_library_item(transcript: Transcript) -> None:
    LibraryItem.objects.filter(user=transcript.user, material_type='transcricao', object_id=transcript.id).update(content=transcript.transcript_only, updated_at=timezone.now())


def _questions_to_markdown(questions: list[dict]) -> str:
    chunks = []
    for idx, question in enumerate(questions, start=1):
        chunks.append(f"## Questão {idx}\n{question.get('statement', '')}")
        alternatives = question.get('alternatives') or []
        if alternatives:
            chunks.append('\n'.join(f'- {alt}' for alt in alternatives))
        if question.get('correct_answer'):
            chunks.append(f"**Gabarito:** {question.get('correct_answer')}")
        if question.get('explanation'):
            chunks.append(f"**Comentário/correção:** {question.get('explanation')}")
    return '\n\n'.join(chunks)


def _flashcards_to_markdown(cards: list[dict]) -> str:
    return '\n\n'.join(f"## Flashcard {idx}\n**Frente:** {card.get('question', '')}\n\n**Verso:** {card.get('answer', '')}" for idx, card in enumerate(cards, start=1))


def _extract_pdf_text(uploaded_file) -> str:
    if not uploaded_file:
        return ''
    try:
        from PyPDF2 import PdfReader
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        text = '\n\n'.join(page.extract_text() or '' for page in reader.pages).strip()
        uploaded_file.seek(0)
        return text
    except Exception as exc:
        return f'Não foi possível extrair o texto do PDF automaticamente. Erro: {exc}'


def _source_from_library_or_transcript(*, transcript=None, library_item=None) -> str:
    if transcript:
        return transcript.best_text
    if library_item:
        return library_item.content
    return ''


def _build_source_text_from_uploads(*, title: str, subject: str, area: str, input_text: str = '', pdf_file=None, audio_files=None) -> str:
    parts: list[str] = []
    if input_text:
        parts.append('## Texto/orientação informada\n' + input_text)
    if pdf_file:
        parts.append('## PDF/material da aula\n' + _extract_pdf_text(pdf_file))
    for idx, audio in enumerate(audio_files or [], start=1):
        try:
            raw = transcribe_uploaded_file(audio, title=f'{title} — áudio {idx}', subject=subject, area=area)
            parts.append(f'## Transcrição do áudio {idx}\n' + extract_transcript_only(raw))
        except Exception as exc:
            parts.append(f'## Áudio {idx}\nNão foi possível transcrever este arquivo. Detalhe: {exc}')
    return '\n\n'.join(part for part in parts if part.strip()).strip()


def _question_correct_letter(question: Question) -> str:
    answer = (question.correct_answer or '').strip()
    if not answer:
        return ''
    return answer[0].upper()


def _is_answer_correct(question: Question, selected: str) -> bool:
    selected = (selected or '').strip().upper()[:1]
    return bool(selected and selected == _question_correct_letter(question))


def _update_exam_score(exam: Exam) -> None:
    total = exam.questions.count()
    answered = exam.answers.count()
    correct = exam.answers.filter(is_correct=True).count()
    exam.score = round((correct / total) * 100, 2) if total else 0
    if total and answered >= total:
        exam.finished_at = timezone.now()
    exam.suggestion = f'Acertos: {correct}. Erros: {max(0, answered - correct)}. Total respondido: {answered}/{total}. Revise as questões erradas e gere flashcards dos temas com maior erro.'
    exam.save(update_fields=['score', 'finished_at', 'suggestion', 'updated_at'])


@login_required
def dashboard(request):
    summaries = Summary.objects.filter(user=request.user)
    questions = Question.objects.filter(user=request.user)
    transcripts = Transcript.objects.filter(user=request.user)
    flashcards = Flashcard.objects.filter(user=request.user)
    exams = Exam.objects.filter(user=request.user)
    study_plans = StudyPlan.objects.filter(user=request.user)
    library_items = LibraryItem.objects.filter(user=request.user)[:6]
    weekly_start = timezone.now() - timezone.timedelta(days=7)
    weekly_count = LibraryItem.objects.filter(user=request.user, created_at__gte=weekly_start).count()
    hits = sum(card.hits for card in flashcards)
    misses = sum(card.misses for card in flashcards)
    context = {
        'summary_count': summaries.count(), 'question_count': questions.count(), 'transcript_count': transcripts.count(),
        'flashcard_count': flashcards.count(), 'exam_count': exams.count(), 'study_plan_count': study_plans.count(),
        'weekly_count': weekly_count, 'weekly_progress': min(weekly_count * 10, 100), 'latest_items': library_items,
        'direito_subjects': DIREITO_SUBJECTS, 'medicina_subjects': MEDICINA_SUBJECTS, 'geral_subjects': GERAL_SUBJECTS,
        'flash_hits': hits, 'flash_misses': misses,
    }
    return render(request, 'studies/dashboard.html', context)


@login_required
def generate_summary(request):
    result = None
    library_item = None
    if request.method == 'POST':
        form = SummaryForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            source_text = data.get('input_text') or data['title']
            if data['source_type'] == 'pdf':
                source_text = _extract_pdf_text(data['pdf_file'])
            elif data['source_type'] == 'pdf_audio':
                source_text = _build_source_text_from_uploads(title=data['title'], subject=data.get('subject') or '', area=data['area'], input_text=data.get('input_text') or '', pdf_file=data.get('pdf_file'), audio_files=data.get('audio_files') or [])
            elif data['source_type'] == 'transcricao':
                source_text = data['transcript'].best_text
            result = ai_generate_summary(area=data['area'], title=data['title'], subject=data.get('subject') or '', input_text=source_text, summary_type=data['summary_type'], level=data['level'])
            summary = Summary.objects.create(user=request.user, title=data['title'], area=data['area'], subject=data.get('subject') or '', source_type=data['source_type'], summary_type=data['summary_type'], level=data['level'], input_text=source_text, content=result, folder=data.get('folder'))
            library_item = _create_library_item(user=request.user, title=summary.title, material_type='resumo', area=summary.area, subject=summary.subject, content=summary.content, folder=summary.folder, object_id=summary.id)
            messages.success(request, 'Resumo completo gerado e salvo na biblioteca.')
        else:
            messages.error(request, 'Revise os campos do formulário.')
    else:
        form = SummaryForm(user=request.user, initial={'level': 'avancado', 'summary_type': 'completo'})
    return render(request, 'studies/generate_summary.html', {'form': form, 'result': result, 'library_item': library_item})


@login_required
def create_questions(request):
    generated = []
    library_item = None
    if request.method == 'POST':
        form = QuestionGenerationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            source_text = data.get('source_text') or ''
            source_text += '\n\n' + _source_from_library_or_transcript(transcript=data.get('transcript'), library_item=data.get('library_item'))
            if data.get('pdf_file'):
                source_text += '\n\n' + _extract_pdf_text(data['pdf_file'])
            generated = ai_generate_questions(area=data['area'], subject=data['subject'], quantity=data['quantity'], difficulty=data['difficulty'], question_type=data['question_type'], include_answer=data['include_answer'], include_explanation=data['include_explanation'], source_text=source_text)
            first_question = None
            for idx, item in enumerate(generated, start=1):
                question = Question.objects.create(user=request.user, title=f"{data['subject']} — Questão {idx}", area=data['area'], subject=data['subject'], statement=item.get('statement', ''), alternatives=item.get('alternatives') or [], correct_answer=item.get('correct_answer', ''), explanation=item.get('explanation', ''), difficulty=data['difficulty'], question_type=data['question_type'], folder=data.get('folder'))
                first_question = first_question or question
            content = _questions_to_markdown(generated)
            library_item = _create_library_item(user=request.user, title=f"Questões — {data['subject']}", material_type='questao', area=data['area'], subject=data['subject'], content=content, folder=data.get('folder'), object_id=first_question.id if first_question else None)
            messages.success(request, 'Questões geradas e salvas na biblioteca.')
        else:
            messages.error(request, 'Revise os campos do formulário.')
    else:
        form = QuestionGenerationForm(user=request.user)
    return render(request, 'studies/create_questions.html', {'form': form, 'generated': generated, 'library_item': library_item})


@login_required
def transcriptions(request):
    transcript = None
    if request.method == 'POST':
        form = TranscriptForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            uploaded = data['file']
            try:
                raw_text = transcribe_uploaded_file(uploaded, title=data['title'], subject=data.get('subject') or '', area=data['area'])
                professor_text = _extract_transcript_only(raw_text)
                status = 'demonstrativa' if is_demo_transcription(raw_text) else 'concluida'
                summary_text = ai_generate_summary(area=data['area'], title=f"Resumo — {data['title']}", subject=data.get('subject') or '', input_text=professor_text, summary_type='completo', level='avancado')
                try:
                    uploaded.seek(0)
                except Exception:
                    pass
                transcript = Transcript.objects.create(user=request.user, title=data['title'], area=data['area'], subject=data.get('subject') or '', source_file=uploaded, raw_text=raw_text, professor_text=professor_text, summary_text=summary_text, folder=data.get('folder'), status=status)
                _create_library_item(user=request.user, title=transcript.title, material_type='transcricao', area=transcript.area, subject=transcript.subject, content=transcript.transcript_only, folder=transcript.folder, object_id=transcript.id)
                messages.success(request, 'Transcrição concluída. A fala do professor foi salva separada do resumo explicativo.')
            except Exception as exc:
                messages.error(request, f'Deu erro ao transcrever. Detalhe técnico: {exc}')
                return redirect('studies:transcriptions')
        else:
            messages.error(request, 'Revise o formulário de transcrição.')
    else:
        form = TranscriptForm(user=request.user)
    recent = Transcript.objects.filter(user=request.user)[:5]
    return render(request, 'studies/transcriptions.html', {'form': form, 'transcript': transcript, 'recent': recent})


@login_required
def transcript_detail(request, pk: int):
    transcript = get_object_or_404(Transcript, pk=pk, user=request.user)
    return render(request, 'studies/transcript_detail.html', {'transcript': transcript})


@login_required
def transcript_action(request, pk: int, action: str):
    transcript = get_object_or_404(Transcript, pk=pk, user=request.user)
    if action == 'retranscrever':
        if not transcript.source_file:
            messages.error(request, 'Não há arquivo original salvo para retranscrever. Envie a aula novamente.')
            return redirect('studies:transcript_detail', pk=transcript.id)
        try:
            transcript.source_file.open('rb')
            raw_text = transcribe_uploaded_file(transcript.source_file, title=transcript.title, subject=transcript.subject or '', area=transcript.area)
        except Exception as exc:
            messages.error(request, f'Não foi possível retranscrever o arquivo original: {exc}')
            return redirect('studies:transcript_detail', pk=transcript.id)
        finally:
            try:
                transcript.source_file.close()
            except Exception:
                pass
        professor_text = extract_transcript_only(raw_text)
        status = 'demonstrativa' if is_demo_transcription(raw_text) else 'concluida'
        summary_text = ai_generate_summary(area=transcript.area, title=f'Resumo — {transcript.title}', subject=transcript.subject, input_text=professor_text, summary_type='completo', level='avancado')
        transcript.raw_text = raw_text
        transcript.professor_text = professor_text
        transcript.corrected_text = ''
        transcript.topics_text = ''
        transcript.summary_text = summary_text
        transcript.status = status
        transcript.save(update_fields=['raw_text', 'professor_text', 'corrected_text', 'topics_text', 'summary_text', 'status', 'updated_at'])
        _sync_transcript_library_item(transcript)
        messages.success(request, 'Aula retranscrita e limpa. As marcações de parte não aparecem mais na transcrição principal.')
        return redirect('studies:transcript_detail', pk=transcript.id)
    if action == 'reprocessar':
        transcript.professor_text = extract_transcript_only(transcript.raw_text)
        transcript.status = 'demonstrativa' if is_demo_transcription(transcript.raw_text) else 'concluida'
        transcript.save(update_fields=['professor_text', 'status', 'updated_at'])
        _sync_transcript_library_item(transcript)
        messages.success(request, 'Transcrição limpa novamente a partir do texto bruto salvo.')
        return redirect('studies:transcript_detail', pk=transcript.id)
    if action == 'corrigir':
        transcript.corrected_text = correct_transcript(transcript.best_text, transcript.area)
        transcript.save(update_fields=['corrected_text', 'updated_at'])
        _sync_transcript_library_item(transcript)
        messages.success(request, 'Texto corrigido com sucesso.')
        return redirect('studies:transcript_detail', pk=transcript.id)
    if action == 'topicos':
        transcript.topics_text = split_topics(transcript.best_text, transcript.area)
        transcript.save(update_fields=['topics_text', 'updated_at'])
        messages.success(request, 'Transcrição separada por tópicos.')
        return redirect('studies:transcript_detail', pk=transcript.id)
    if action == 'resumo':
        content = ai_generate_summary(area=transcript.area, title=f'Resumo — {transcript.title}', subject=transcript.subject, input_text=transcript.transcript_only, summary_type='completo', level='avancado')
        transcript.summary_text = content
        transcript.save(update_fields=['summary_text', 'updated_at'])
        summary = Summary.objects.create(user=request.user, title=f'Resumo — {transcript.title}', area=transcript.area, subject=transcript.subject, source_type='transcricao', summary_type='completo', level='avancado', input_text=transcript.transcript_only, content=content, folder=transcript.folder)
        item = _create_library_item(user=request.user, title=summary.title, material_type='resumo', area=summary.area, subject=summary.subject, content=summary.content, folder=summary.folder, object_id=summary.id)
        messages.success(request, 'Resumo avançado da transcrição criado.')
        return redirect('studies:library_detail', pk=item.id)
    if action == 'questoes':
        questions = ai_generate_questions(area=transcript.area, subject=transcript.subject or transcript.title, quantity=8, difficulty='media', question_type='multipla', include_answer=True, include_explanation=True, source_text=transcript.best_text)
        content = _questions_to_markdown(questions)
        item = _create_library_item(user=request.user, title=f'Questões — {transcript.title}', material_type='questao', area=transcript.area, subject=transcript.subject, content=content, folder=transcript.folder, object_id=transcript.id)
        messages.success(request, 'Questões da transcrição criadas.')
        return redirect('studies:library_detail', pk=item.id)
    if action == 'flashcards':
        cards = ai_generate_flashcards(area=transcript.area, subject=transcript.subject or transcript.title, quantity=12, difficulty='media', source_text=transcript.best_text)
        for card in cards:
            Flashcard.objects.create(user=request.user, question=card.get('question', ''), answer=card.get('answer', ''), area=transcript.area, subject=transcript.subject, difficulty='media', folder=transcript.folder)
        item = _create_library_item(user=request.user, title=f'Flashcards — {transcript.title}', material_type='flashcard', area=transcript.area, subject=transcript.subject, content=_flashcards_to_markdown(cards), folder=transcript.folder, object_id=transcript.id)
        messages.success(request, 'Flashcards da transcrição criados.')
        return redirect('studies:library_detail', pk=item.id)
    raise Http404('Ação não encontrada.')


@login_required
def library(request):
    if request.method == 'POST':
        folder_form = FolderForm(request.POST)
        if folder_form.is_valid():
            folder = folder_form.save(commit=False)
            folder.user = request.user
            folder.save()
            messages.success(request, 'Pasta criada com sucesso.')
            return redirect('studies:library')
    folder_form = FolderForm()
    filter_form = LibraryFilterForm(request.GET or None)
    items = LibraryItem.objects.filter(user=request.user)
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        if data.get('area'):
            items = items.filter(area=data['area'])
        if data.get('material_type'):
            items = items.filter(material_type=data['material_type'])
        if data.get('subject'):
            items = items.filter(subject__icontains=data['subject'])
        if data.get('favorites'):
            items = items.filter(favorite=True)
    folders = Folder.objects.filter(user=request.user)
    latest_items = items[:3]
    return render(request, 'studies/library.html', {'items': items, 'latest_items': latest_items, 'filter_form': filter_form, 'folder_form': folder_form, 'folders': folders})


@login_required
def library_detail(request, pk: int):
    item = get_object_or_404(LibraryItem, pk=pk, user=request.user)
    transcript_obj = Transcript.objects.filter(pk=item.object_id, user=request.user).first() if item.material_type == 'transcricao' and item.object_id else None
    return render(request, 'studies/library_detail.html', {'item': item, 'transcript_obj': transcript_obj})


@login_required
@require_POST
def library_delete(request, pk: int):
    item = get_object_or_404(LibraryItem, pk=pk, user=request.user)
    item.delete()
    messages.success(request, 'Item removido da biblioteca.')
    return redirect('studies:library')


@login_required
@require_POST
def library_toggle_favorite(request, pk: int):
    item = get_object_or_404(LibraryItem, pk=pk, user=request.user)
    item.favorite = not item.favorite
    item.save(update_fields=['favorite', 'updated_at'])
    return redirect(request.POST.get('next') or 'studies:library')


@login_required
def export_library_item(request, pk: int, file_format: str):
    if file_format not in {'docx', 'pdf', 'txt'}:
        raise Http404('Formato inválido.')
    item = get_object_or_404(LibraryItem, pk=pk, user=request.user)
    export_text = item.content
    if item.material_type == 'transcricao' and item.object_id:
        transcript_obj = Transcript.objects.filter(pk=item.object_id, user=request.user).first()
        if transcript_obj:
            export_text = transcript_obj.transcript_only
    path = export_content(user=request.user, title=item.title, area=item.get_area_display(), subject=item.subject, content=export_text, file_format=file_format)
    export = Export.objects.create(user=request.user, title=item.title, material_type=item.material_type, file_format=file_format)
    with path.open('rb') as handle:
        export.file.save(path.name, File(handle), save=True)
    return FileResponse(open(path, 'rb'), as_attachment=True, filename=path.name)


@login_required
def flashcards(request):
    generated = []
    library_item = None
    if request.method == 'POST':
        form = FlashcardGenerationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            source_text = data.get('source_text') or ''
            if data.get('pdf_file'):
                source_text += '\n\n' + _extract_pdf_text(data['pdf_file'])
            if data.get('library_item'):
                source_text += '\n\n' + data['library_item'].content
            generated = ai_generate_flashcards(area=data['area'], subject=data['subject'], quantity=data['quantity'], difficulty=data['difficulty'], source_text=source_text)
            for card in generated:
                Flashcard.objects.create(user=request.user, question=card.get('question', ''), answer=card.get('answer', ''), area=data['area'], subject=data['subject'], difficulty=data['difficulty'])
            library_item = _create_library_item(user=request.user, title=f"Flashcards — {data['subject']}", material_type='flashcard', area=data['area'], subject=data['subject'], content=_flashcards_to_markdown(generated))
            messages.success(request, 'Flashcards gerados e salvos.')
    else:
        form = FlashcardGenerationForm(user=request.user)
    cards = Flashcard.objects.filter(user=request.user)[:30]
    hits = sum(card.hits for card in Flashcard.objects.filter(user=request.user))
    misses = sum(card.misses for card in Flashcard.objects.filter(user=request.user))
    total = hits + misses
    accuracy = round((hits / total) * 100) if total else 0
    return render(request, 'studies/flashcards.html', {'form': form, 'generated': generated, 'cards': cards, 'library_item': library_item, 'hits': hits, 'misses': misses, 'total_reviewed': total, 'accuracy': accuracy})


@login_required
@require_POST
def review_flashcard(request, pk: int, result: str):
    card = get_object_or_404(Flashcard, pk=pk, user=request.user)
    if result == 'hit':
        card.hits += 1
    elif result == 'miss':
        card.misses += 1
    card.review_date = timezone.localdate() + timezone.timedelta(days=2 if result == 'hit' else 1)
    card.save(update_fields=['hits', 'misses', 'review_date', 'updated_at'])
    messages.success(request, 'Revisão registrada.')
    return redirect('studies:flashcards')


@login_required
def simulations(request):
    generated = []
    exam = None
    library_item = None
    if request.method == 'POST':
        form = ExamGenerationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            data = form.cleaned_data
            source_text = data.get('source_text') or ''
            if data.get('pdf_file'):
                source_text += '\n\n' + _extract_pdf_text(data['pdf_file'])
            if data.get('library_item'):
                source_text += '\n\n' + data['library_item'].content
            generated = ai_generate_questions(area=data['area'], subject=data['subject'], quantity=data['quantity'], difficulty=data['difficulty'], question_type='multipla', include_answer=True, include_explanation=True, source_text=source_text)
            exam = Exam.objects.create(user=request.user, title=f"Simulado — {data['subject']}", area=data['area'], subject=data['subject'], difficulty=data['difficulty'])
            for idx, item in enumerate(generated, start=1):
                question = Question.objects.create(user=request.user, title=f"Simulado {data['subject']} — Q{idx}", area=data['area'], subject=data['subject'], statement=item.get('statement', ''), alternatives=item.get('alternatives') or [], correct_answer=item.get('correct_answer', ''), explanation=item.get('explanation', ''), difficulty=data['difficulty'], question_type='multipla')
                exam.questions.add(question)
            content = _questions_to_markdown(generated)
            library_item = _create_library_item(user=request.user, title=exam.title, material_type='simulado', area=exam.area, subject=exam.subject, content=content, object_id=exam.id)
            messages.success(request, 'Simulado criado. Agora você pode responder online.')
            return redirect('studies:exam_detail', pk=exam.id)
    else:
        form = ExamGenerationForm(user=request.user)
    exams = Exam.objects.filter(user=request.user)[:10]
    return render(request, 'studies/simulations.html', {'form': form, 'generated': generated, 'exam': exam, 'exams': exams, 'library_item': library_item})


@login_required
def exam_detail(request, pk: int):
    exam = get_object_or_404(Exam, pk=pk, user=request.user)
    if request.method == 'POST':
        question = get_object_or_404(Question, pk=request.POST.get('question_id'), user=request.user)
        selected = request.POST.get('selected_answer', '')
        if question not in exam.questions.all():
            raise Http404('Questão não pertence a este simulado.')
        answer, _ = ExamAnswer.objects.update_or_create(user=request.user, exam=exam, question=question, defaults={'selected_answer': selected, 'is_correct': _is_answer_correct(question, selected)})
        _update_exam_score(exam)
        messages.success(request, 'Resposta registrada: ' + ('acertou.' if answer.is_correct else 'errou. Confira o gabarito comentado.'))
        return redirect('studies:exam_detail', pk=exam.id)
    answers = {answer.question_id: answer for answer in exam.answers.all()}
    rows = [{'question': q, 'answer': answers.get(q.id), 'correct_letter': _question_correct_letter(q)} for q in exam.questions.all()]
    correct = exam.answers.filter(is_correct=True).count()
    answered = exam.answers.count()
    total = exam.questions.count()
    wrong = max(0, answered - correct)
    return render(request, 'studies/exam_detail.html', {'exam': exam, 'rows': rows, 'answered': answered, 'correct': correct, 'wrong': wrong, 'total': total})


@login_required
def study_plan(request):
    plan = None
    library_item = None
    profile = getattr(request.user, 'profile', None)
    if request.method == 'POST':
        form = StudyPlanForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            profile_context = ''
            if profile:
                profile_context = f"\nPerfil: {profile.full_name}; curso {profile.get_study_area_display()}; faculdade {profile.college}; objetivo/rotina {profile.objective}."
            obj.content = generate_study_plan(area=obj.area, course=obj.course, subjects=obj.subjects + profile_context, exam_date=obj.exam_date, daily_minutes=obj.daily_minutes, difficulty=obj.difficulty, objective=obj.objective)
            obj.save()
            plan = obj
            library_item = _create_library_item(user=request.user, title=obj.title, material_type='plano', area=obj.area, subject=obj.course, content=obj.content, object_id=obj.id)
            messages.success(request, 'Plano de estudos gerado e salvo.')
    else:
        initial_subjects = '\n'.join(DIREITO_SUBJECTS[:4])
        form = StudyPlanForm(initial={'daily_minutes': 90, 'subjects': initial_subjects})
    plans = StudyPlan.objects.filter(user=request.user)[:10]
    return render(request, 'studies/study_plan.html', {'form': form, 'plan': plan, 'plans': plans, 'library_item': library_item})
