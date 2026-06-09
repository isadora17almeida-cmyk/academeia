from django import forms
from django.conf import settings
from .models import AreaChoices, DifficultyChoices, Folder, Flashcard, LibraryItem, Question, StudyPlan, Summary, Transcript

COMMON_ATTR = {'class': 'form-control'}


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            if self.required:
                raise forms.ValidationError(self.error_messages['required'], code='required')
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return [super(MultipleFileField, self).clean(item, initial) for item in data]




def _validate_uploaded_file(uploaded, *, allowed_extensions: list[str], label: str = 'Arquivo'):
    """Valida extensão e tamanho por arquivo, mantendo erro amigável na tela."""
    name = (getattr(uploaded, 'name', '') or '').lower()
    if not any(name.endswith(ext) for ext in allowed_extensions):
        allowed_text = ', '.join(ext.upper().replace('.', '') for ext in allowed_extensions)
        raise forms.ValidationError(f'{label} em formato não permitido. Use {allowed_text}.')
    max_mb = int(getattr(settings, 'MAX_UPLOAD_MB', 250))
    size = getattr(uploaded, 'size', 0) or 0
    if size > max_mb * 1024 * 1024:
        raise forms.ValidationError(f'{label} muito grande ({size / 1024 / 1024:.1f} MB). O limite por arquivo é {max_mb} MB.')
    return uploaded


def _validate_uploaded_files(files, *, allowed_extensions: list[str], label: str = 'Arquivo'):
    files = list(files or [])
    max_total_mb = int(getattr(settings, 'MAX_TOTAL_UPLOAD_MB', getattr(settings, 'MAX_UPLOAD_MB', 250)))
    total_size = sum((getattr(item, 'size', 0) or 0) for item in files)
    if total_size > max_total_mb * 1024 * 1024:
        raise forms.ValidationError(f'O envio tem {total_size / 1024 / 1024:.1f} MB no total. O limite total atual é {max_total_mb} MB. Envie menos arquivos por vez ou comprima os arquivos.')
    return [_validate_uploaded_file(item, allowed_extensions=allowed_extensions, label=f'{label} {idx}') for idx, item in enumerate(files, start=1)]


PDF_EXTENSIONS = ['.pdf']
AUDIO_VIDEO_TEXT_EXTENSIONS = ['.mp3', '.wav', '.m4a', '.mp4', '.aac', '.ogg', '.webm', '.mov', '.flac', '.txt']
MATERIAL_EXTENSIONS = ['.pdf', '.txt']

class SummaryForm(forms.Form):
    area = forms.ChoiceField(label='Área/curso', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    source_type = forms.ChoiceField(label='Tipo de conteúdo principal', choices=[
        ('assunto_digitado', 'Assunto digitado'),
        ('texto_colado', 'Texto colado'),
        ('pdf_audio', 'PDF/material + áudio(s) da aula'),
        ('pdf', 'PDF enviado'),
        ('transcricao', 'Transcrição salva'),
    ], widget=forms.Select(attrs=COMMON_ATTR))
    summary_type = forms.ChoiceField(label='Tipo de resumo', choices=Summary.SUMMARY_TYPES, widget=forms.Select(attrs=COMMON_ATTR))
    level = forms.ChoiceField(label='Nível', choices=Summary.LEVELS, initial='avancado', widget=forms.Select(attrs=COMMON_ATTR))
    title = forms.CharField(label='Título', max_length=180, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Aula 04 - Responsabilidade Civil'}))
    subject = forms.CharField(label='Matéria', max_length=140, required=False, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Civil, Anatomia, Administração'}))
    input_text = forms.CharField(label='Texto ou orientação adicional', required=False, widget=forms.Textarea(attrs={**COMMON_ATTR, 'rows': 6, 'placeholder': 'Cole conteúdo, roteiro, observações ou instruções específicas.'}))
    pdf_files = MultipleFileField(label='PDF(s)/material(is) da aula', required=False, widget=MultipleFileInput(attrs={**COMMON_ATTR, 'accept': '.pdf', 'multiple': True}))
    audio_files = MultipleFileField(label='Áudio(s)/vídeo(s) da aula', required=False, widget=MultipleFileInput(attrs={**COMMON_ATTR, 'accept': '.mp3,.wav,.m4a,.mp4,.aac,.ogg,.webm,.mov,.flac,.txt', 'multiple': True}))
    transcript = forms.ModelChoiceField(label='Transcrição salva', queryset=Transcript.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))
    folder = forms.ModelChoiceField(label='Pasta', queryset=Folder.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['transcript'].queryset = Transcript.objects.filter(user=user)
        self.fields['folder'].queryset = Folder.objects.filter(user=user)

    def clean(self):
        cleaned = super().clean()
        source_type = cleaned.get('source_type')
        input_text = cleaned.get('input_text')
        pdf_files = cleaned.get('pdf_files') or []
        audio_files = cleaned.get('audio_files') or []
        transcript = cleaned.get('transcript')
        title = cleaned.get('title')
        if source_type in ['assunto_digitado', 'texto_colado'] and not (input_text or title):
            raise forms.ValidationError('Digite um assunto ou cole um conteúdo para gerar o resumo.')
        if source_type == 'pdf' and not pdf_files:
            raise forms.ValidationError('Envie um PDF para gerar o resumo.')
        if source_type == 'pdf_audio' and not (pdf_files or audio_files or input_text):
            raise forms.ValidationError('Envie pelo menos um PDF, áudio/vídeo ou texto base.')
        if source_type == 'transcricao' and not transcript:
            raise forms.ValidationError('Selecione uma transcrição salva.')
        return cleaned


class QuestionGenerationForm(forms.Form):
    area = forms.ChoiceField(label='Área/curso', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Assunto', max_length=140, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: solidariedade, pâncreas, orçamento público'}))
    quantity = forms.IntegerField(label='Quantidade de questões', min_value=1, max_value=30, initial=5, widget=forms.NumberInput(attrs=COMMON_ATTR))
    difficulty = forms.ChoiceField(label='Dificuldade', choices=DifficultyChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    question_type = forms.ChoiceField(label='Tipo de questão', choices=Question.QUESTION_TYPES, widget=forms.Select(attrs=COMMON_ATTR))
    source_text = forms.CharField(label='Texto base opcional', required=False, widget=forms.Textarea(attrs={**COMMON_ATTR, 'rows': 5, 'placeholder': 'Cole resumo, transcrição ou conteúdo para usar como base.'}))
    pdf_files = MultipleFileField(label='PDF(s)/material(is) para base das questões', required=False, widget=MultipleFileInput(attrs={**COMMON_ATTR, 'accept': '.pdf,.txt', 'multiple': True}))
    transcript = forms.ModelChoiceField(label='Transcrição salva', queryset=Transcript.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))
    library_item = forms.ModelChoiceField(label='Material da biblioteca', queryset=LibraryItem.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))
    include_answer = forms.BooleanField(label='Incluir gabarito', required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'check-control'}))
    include_explanation = forms.BooleanField(label='Incluir comentário/correção', required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'check-control'}))
    folder = forms.ModelChoiceField(label='Pasta', queryset=Folder.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(user=user)
        self.fields['transcript'].queryset = Transcript.objects.filter(user=user)
        self.fields['library_item'].queryset = LibraryItem.objects.filter(user=user)


class TranscriptForm(forms.Form):
    title = forms.CharField(label='Nome da aula', max_length=180, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Aula 04 - Responsabilidade Civil'}))
    subject = forms.CharField(label='Matéria', max_length=140, required=False, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Civil, Anatomia'}))
    area = forms.ChoiceField(label='Área/curso', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    files = MultipleFileField(label='Arquivo(s) de áudio, vídeo ou texto', widget=MultipleFileInput(attrs={**COMMON_ATTR, 'accept': '.mp3,.wav,.m4a,.mp4,.aac,.ogg,.webm,.mov,.flac,.txt', 'multiple': True}))
    folder = forms.ModelChoiceField(label='Pasta', queryset=Folder.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(user=user)

    def clean_files(self):
        uploaded_files = self.cleaned_data.get('files') or []
        return _validate_uploaded_files(uploaded_files, allowed_extensions=AUDIO_VIDEO_TEXT_EXTENSIONS, label='Arquivo')


class FlashcardGenerationForm(forms.Form):
    area = forms.ChoiceField(label='Área/curso', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Assunto', max_length=140, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: obrigação solidária, farmacologia, contabilidade'}))
    quantity = forms.IntegerField(label='Quantidade', min_value=1, max_value=50, initial=10, widget=forms.NumberInput(attrs=COMMON_ATTR))
    difficulty = forms.ChoiceField(label='Dificuldade', choices=DifficultyChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    source_text = forms.CharField(label='Resumo/transcrição opcional', required=False, widget=forms.Textarea(attrs={**COMMON_ATTR, 'rows': 6, 'placeholder': 'Cole um resumo ou transcrição para gerar flashcards precisos.'}))
    pdf_files = MultipleFileField(label='PDF(s) da aula ou resumo', required=False, widget=MultipleFileInput(attrs={**COMMON_ATTR, 'accept': '.pdf,.txt', 'multiple': True}))
    library_item = forms.ModelChoiceField(label='Material da biblioteca', queryset=LibraryItem.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['library_item'].queryset = LibraryItem.objects.filter(user=user)


class StudyPlanForm(forms.ModelForm):
    class Meta:
        model = StudyPlan
        fields = ('title', 'area', 'course', 'subjects', 'exam_date', 'daily_minutes', 'difficulty', 'objective')
        widgets = {
            'title': forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Plano de Direito Civil para prova'}),
            'area': forms.Select(attrs=COMMON_ATTR),
            'course': forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito, Medicina'}),
            'subjects': forms.Textarea(attrs={**COMMON_ATTR, 'rows': 7, 'placeholder': 'Uma matéria por linha'}),
            'exam_date': forms.DateInput(attrs={**COMMON_ATTR, 'type': 'date'}),
            'daily_minutes': forms.NumberInput(attrs=COMMON_ATTR),
            'difficulty': forms.Select(attrs=COMMON_ATTR),
            'objective': forms.Select(attrs=COMMON_ATTR),
        }


class FolderForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ('name', 'area', 'description')
        widgets = {
            'name': forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Civil'}),
            'area': forms.Select(attrs=COMMON_ATTR),
            'description': forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Descrição opcional'}),
        }


class LibraryFilterForm(forms.Form):
    area = forms.ChoiceField(label='Área', choices=[('', 'Todas')] + list(AreaChoices.choices), required=False, widget=forms.Select(attrs=COMMON_ATTR))
    material_type = forms.ChoiceField(label='Tipo', choices=[('', 'Todos'), ('resumo', 'Resumo'), ('questao', 'Questão'), ('transcricao', 'Transcrição'), ('flashcard', 'Flashcard'), ('simulado', 'Simulado'), ('plano', 'Plano de estudos')], required=False, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Matéria', required=False, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Filtrar por matéria'}))
    favorites = forms.BooleanField(label='Somente favoritos', required=False, widget=forms.CheckboxInput(attrs={'class': 'check-control'}))


class ExamGenerationForm(forms.Form):
    area = forms.ChoiceField(label='Área/curso', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Assunto', max_length=140, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Constitucional, Fisiologia'}))
    quantity = forms.IntegerField(label='Quantidade de questões', min_value=1, max_value=50, initial=10, widget=forms.NumberInput(attrs=COMMON_ATTR))
    difficulty = forms.ChoiceField(label='Dificuldade', choices=DifficultyChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    source_text = forms.CharField(label='Texto base opcional', required=False, widget=forms.Textarea(attrs={**COMMON_ATTR, 'rows': 5, 'placeholder': 'Cole transcrição, resumo ou material para basear o simulado.'}))
    pdf_files = MultipleFileField(label='PDF(s)/documento(s) da aula', required=False, widget=MultipleFileInput(attrs={**COMMON_ATTR, 'accept': '.pdf,.txt', 'multiple': True}))
    library_item = forms.ModelChoiceField(label='Material da biblioteca', queryset=LibraryItem.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['library_item'].queryset = LibraryItem.objects.filter(user=user)


class FlashcardReviewForm(forms.Form):
    result = forms.ChoiceField(choices=[('hit', 'Acertei'), ('miss', 'Errei')], widget=forms.HiddenInput())
