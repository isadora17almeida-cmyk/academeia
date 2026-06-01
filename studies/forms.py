from django import forms
from .models import AreaChoices, DifficultyChoices, Folder, Flashcard, Question, StudyPlan, Summary, Transcript

COMMON_ATTR = {'class': 'form-control'}


class SummaryForm(forms.Form):
    area = forms.ChoiceField(label='Área', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    source_type = forms.ChoiceField(label='Tipo de conteúdo', choices=[
        ('assunto_digitado', 'Assunto digitado'),
        ('texto_colado', 'Texto colado'),
        ('pdf', 'PDF enviado'),
        ('transcricao', 'Transcrição salva'),
    ], widget=forms.Select(attrs=COMMON_ATTR))
    summary_type = forms.ChoiceField(label='Tipo de resumo', choices=Summary.SUMMARY_TYPES, widget=forms.Select(attrs=COMMON_ATTR))
    level = forms.ChoiceField(label='Nível', choices=Summary.LEVELS, widget=forms.Select(attrs=COMMON_ATTR))
    title = forms.CharField(label='Título', max_length=180, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Obrigação de fazer no Direito Civil'}))
    subject = forms.CharField(label='Matéria', max_length=140, required=False, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Civil, Anatomia, Fisiologia'}))
    input_text = forms.CharField(label='Digite o assunto ou cole seu conteúdo', required=False, widget=forms.Textarea(attrs={**COMMON_ATTR, 'rows': 9, 'placeholder': 'Cole seu texto, assunto, roteiro de aula ou observações...'}))
    pdf_file = forms.FileField(label='PDF', required=False, widget=forms.FileInput(attrs={**COMMON_ATTR, 'accept': '.pdf'}))
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
        pdf_file = cleaned.get('pdf_file')
        transcript = cleaned.get('transcript')
        title = cleaned.get('title')
        if source_type in ['assunto_digitado', 'texto_colado'] and not (input_text or title):
            raise forms.ValidationError('Digite um assunto ou cole um conteúdo para gerar o resumo.')
        if source_type == 'pdf' and not pdf_file:
            raise forms.ValidationError('Envie um PDF para gerar o resumo.')
        if source_type == 'transcricao' and not transcript:
            raise forms.ValidationError('Selecione uma transcrição salva.')
        return cleaned


class QuestionGenerationForm(forms.Form):
    area = forms.ChoiceField(label='Área', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Assunto', max_length=140, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: art. 247 do Código Civil, Pâncreas, Diabetes'}))
    quantity = forms.IntegerField(label='Quantidade de questões', min_value=1, max_value=30, initial=5, widget=forms.NumberInput(attrs=COMMON_ATTR))
    difficulty = forms.ChoiceField(label='Dificuldade', choices=DifficultyChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    question_type = forms.ChoiceField(label='Tipo de questão', choices=Question.QUESTION_TYPES, widget=forms.Select(attrs=COMMON_ATTR))
    include_answer = forms.BooleanField(label='Incluir gabarito', required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'check-control'}))
    include_explanation = forms.BooleanField(label='Incluir explicação', required=False, initial=True, widget=forms.CheckboxInput(attrs={'class': 'check-control'}))
    folder = forms.ModelChoiceField(label='Pasta', queryset=Folder.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(user=user)


class TranscriptForm(forms.Form):
    title = forms.CharField(label='Nome da aula', max_length=180, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Aula 04 - Responsabilidade Civil'}))
    subject = forms.CharField(label='Matéria', max_length=140, required=False, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Civil, Anatomia'}))
    area = forms.ChoiceField(label='Área', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    file = forms.FileField(label='Arquivo de áudio ou vídeo', widget=forms.FileInput(attrs={**COMMON_ATTR, 'accept': '.mp3,.wav,.m4a,.mp4,.aac,.ogg,.webm,.mov,.flac,.txt'}))
    folder = forms.ModelChoiceField(label='Pasta', queryset=Folder.objects.none(), required=False, widget=forms.Select(attrs=COMMON_ATTR))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['folder'].queryset = Folder.objects.filter(user=user)

    def clean_file(self):
        uploaded = self.cleaned_data['file']
        allowed = ['.mp3', '.wav', '.m4a', '.mp4', '.aac', '.ogg', '.webm', '.mov', '.flac', '.txt']
        name = uploaded.name.lower()
        if not any(name.endswith(ext) for ext in allowed):
            raise forms.ValidationError('Formato não permitido. Use MP3, WAV, M4A, MP4, AAC, OGG, WEBM, MOV, FLAC ou TXT.')
        return uploaded


class FlashcardGenerationForm(forms.Form):
    area = forms.ChoiceField(label='Área', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Assunto', max_length=140, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: obrigação de fazer, pâncreas, farmacologia'}))
    quantity = forms.IntegerField(label='Quantidade', min_value=1, max_value=50, initial=10, widget=forms.NumberInput(attrs=COMMON_ATTR))
    difficulty = forms.ChoiceField(label='Dificuldade', choices=DifficultyChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    source_text = forms.CharField(label='Texto base opcional', required=False, widget=forms.Textarea(attrs={**COMMON_ATTR, 'rows': 6, 'placeholder': 'Cole um resumo ou transcrição para gerar flashcards mais precisos.'}))


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
    favorites = forms.BooleanField(label='Favoritos', required=False, widget=forms.CheckboxInput(attrs={'class': 'check-control'}))


class ExamGenerationForm(forms.Form):
    area = forms.ChoiceField(label='Área', choices=AreaChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))
    subject = forms.CharField(label='Assunto', max_length=140, widget=forms.TextInput(attrs={**COMMON_ATTR, 'placeholder': 'Ex.: Direito Constitucional, Fisiologia'}))
    quantity = forms.IntegerField(label='Quantidade de questões', min_value=1, max_value=50, initial=10, widget=forms.NumberInput(attrs=COMMON_ATTR))
    difficulty = forms.ChoiceField(label='Dificuldade', choices=DifficultyChoices.choices, widget=forms.Select(attrs=COMMON_ATTR))


class FlashcardReviewForm(forms.Form):
    result = forms.ChoiceField(choices=[('hit', 'Acertei'), ('miss', 'Errei')], widget=forms.HiddenInput())
