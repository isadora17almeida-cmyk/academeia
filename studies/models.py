from django.conf import settings
from django.db import models
from django.utils import timezone


class AreaChoices(models.TextChoices):
    DIREITO = 'direito', 'Direito'
    MEDICINA = 'medicina', 'Medicina'
    GERAL = 'geral', 'Geral'


class DifficultyChoices(models.TextChoices):
    FACIL = 'facil', 'Fácil'
    MEDIA = 'media', 'Média'
    DIFICIL = 'dificil', 'Difícil'


class MaterialTypeChoices(models.TextChoices):
    RESUMO = 'resumo', 'Resumo'
    QUESTAO = 'questao', 'Questão'
    TRANSCRICAO = 'transcricao', 'Transcrição'
    FLASHCARD = 'flashcard', 'Flashcard'
    SIMULADO = 'simulado', 'Simulado'
    PLANO = 'plano', 'Plano de estudos'


class TimeStampedUserModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Folder(TimeStampedUserModel):
    name = models.CharField(max_length=120)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    description = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ('user', 'name')
        verbose_name = 'Pasta'
        verbose_name_plural = 'Pastas'

    def __str__(self):
        return self.name


class Summary(TimeStampedUserModel):
    SUMMARY_TYPES = [
        ('curto', 'Curto'),
        ('medio', 'Médio'),
        ('completo', 'Completo'),
        ('prova', 'Para prova'),
        ('simples', 'Explicação simples'),
        ('mapa_mental', 'Mapa mental em texto'),
        ('vespera', 'Revisão de véspera'),
    ]
    LEVELS = [('basico', 'Básico'), ('intermediario', 'Intermediário'), ('avancado', 'Avançado')]

    title = models.CharField(max_length=180)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    subject = models.CharField(max_length=140, blank=True)
    source_type = models.CharField(max_length=40, default='assunto_digitado')
    summary_type = models.CharField(max_length=30, choices=SUMMARY_TYPES, default='medio')
    level = models.CharField(max_length=30, choices=LEVELS, default='intermediario')
    input_text = models.TextField(blank=True)
    content = models.TextField()
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, blank=True, null=True)
    favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Resumo'
        verbose_name_plural = 'Resumos'

    def __str__(self):
        return self.title


class Question(TimeStampedUserModel):
    QUESTION_TYPES = [
        ('multipla', 'Múltipla escolha'),
        ('vf', 'Verdadeiro ou falso'),
        ('discursiva', 'Discursiva'),
        ('caso_juridico', 'Caso prático jurídico'),
        ('caso_clinico', 'Caso clínico médico'),
    ]

    title = models.CharField(max_length=180)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    subject = models.CharField(max_length=140)
    statement = models.TextField()
    alternatives = models.JSONField(default=list, blank=True)
    correct_answer = models.TextField(blank=True)
    explanation = models.TextField(blank=True)
    difficulty = models.CharField(max_length=20, choices=DifficultyChoices.choices, default=DifficultyChoices.MEDIA)
    question_type = models.CharField(max_length=30, choices=QUESTION_TYPES, default='multipla')
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, blank=True, null=True)
    favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Questão'
        verbose_name_plural = 'Questões'

    def __str__(self):
        return self.title


class Transcript(TimeStampedUserModel):
    title = models.CharField(max_length=180)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    subject = models.CharField(max_length=140, blank=True)
    source_file = models.FileField(upload_to='uploads/transcriptions/', blank=True, null=True)
    raw_text = models.TextField(blank=True, help_text='Texto bruto retornado pela transcrição.')
    professor_text = models.TextField(blank=True, help_text='Transcrição limpa/fiel da fala do professor, sem resumo.')
    summary_text = models.TextField(blank=True, help_text='Resumo automático da aula gerado a partir da transcrição.')
    corrected_text = models.TextField(blank=True)
    topics_text = models.TextField(blank=True)
    status = models.CharField(max_length=30, default='concluida')
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, blank=True, null=True)
    favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Transcrição'
        verbose_name_plural = 'Transcrições'

    def __str__(self):
        return self.title

    @property
    def transcript_only(self):
        """Retorna a fala transcrita do professor sem cortar aulas longas."""
        if self.corrected_text:
            return self.corrected_text
        professor = (self.professor_text or '').strip()
        raw = (self.raw_text or '').strip()
        if raw:
            try:
                from .services.transcription_service import extract_transcript_only
                cleaned_raw = extract_transcript_only(raw)
            except Exception:
                cleaned_raw = raw
            # Proteção para transcrições antigas: se a limpeza anterior cortou o texto,
            # usa o texto bruto limpo mais completo.
            if len(cleaned_raw) > len(professor) + 250:
                return cleaned_raw
        return professor or raw

    @property
    def best_text(self):
        return self.transcript_only

    @property
    def full_study_text(self):
        parts = []
        if self.transcript_only:
            parts.append('## Transcrição do professor\n' + self.transcript_only)
        if self.summary_text:
            parts.append('## Resumo da aula\n' + self.summary_text)
        if self.topics_text:
            parts.append('## Tópicos organizados\n' + self.topics_text)
        return '\n\n'.join(parts)


class Flashcard(TimeStampedUserModel):
    question = models.TextField()
    answer = models.TextField()
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    subject = models.CharField(max_length=140, blank=True)
    difficulty = models.CharField(max_length=20, choices=DifficultyChoices.choices, default=DifficultyChoices.MEDIA)
    review_date = models.DateField(default=timezone.localdate)
    hits = models.PositiveIntegerField(default=0)
    misses = models.PositiveIntegerField(default=0)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, blank=True, null=True)
    favorite = models.BooleanField(default=False)

    class Meta:
        ordering = ['review_date', '-created_at']
        verbose_name = 'Flashcard'
        verbose_name_plural = 'Flashcards'

    def __str__(self):
        return self.question[:80]


class Exam(TimeStampedUserModel):
    title = models.CharField(max_length=180)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    subject = models.CharField(max_length=140)
    difficulty = models.CharField(max_length=20, choices=DifficultyChoices.choices, default=DifficultyChoices.MEDIA)
    questions = models.ManyToManyField(Question, blank=True, related_name='exams')
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    time_spent_seconds = models.PositiveIntegerField(default=0)
    finished_at = models.DateTimeField(blank=True, null=True)
    suggestion = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Simulado'
        verbose_name_plural = 'Simulados'

    def __str__(self):
        return self.title


class ExamAnswer(TimeStampedUserModel):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.TextField(blank=True)
    is_correct = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Resposta do simulado'
        verbose_name_plural = 'Respostas dos simulados'


class StudyPlan(TimeStampedUserModel):
    OBJECTIVES = [
        ('faculdade', 'Prova da faculdade'),
        ('oab', 'OAB'),
        ('residencia', 'Residência'),
        ('concurso', 'Concurso'),
        ('revisao', 'Revisão geral'),
    ]

    title = models.CharField(max_length=180)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    course = models.CharField(max_length=140, blank=True)
    subjects = models.TextField(help_text='Uma matéria por linha')
    exam_date = models.DateField(blank=True, null=True)
    daily_minutes = models.PositiveIntegerField(default=60)
    difficulty = models.CharField(max_length=20, choices=DifficultyChoices.choices, default=DifficultyChoices.MEDIA)
    objective = models.CharField(max_length=30, choices=OBJECTIVES, default='faculdade')
    content = models.TextField()
    progress = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Plano de estudos'
        verbose_name_plural = 'Planos de estudos'

    def __str__(self):
        return self.title


class LibraryItem(TimeStampedUserModel):
    title = models.CharField(max_length=180)
    material_type = models.CharField(max_length=30, choices=MaterialTypeChoices.choices)
    area = models.CharField(max_length=20, choices=AreaChoices.choices, default=AreaChoices.GERAL)
    subject = models.CharField(max_length=140, blank=True)
    content = models.TextField(blank=True)
    folder = models.ForeignKey(Folder, on_delete=models.SET_NULL, blank=True, null=True)
    favorite = models.BooleanField(default=False)
    object_id = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Item da biblioteca'
        verbose_name_plural = 'Itens da biblioteca'

    def __str__(self):
        return self.title


class Export(TimeStampedUserModel):
    FORMAT_CHOICES = [('docx', 'Word'), ('pdf', 'PDF'), ('txt', 'TXT')]

    title = models.CharField(max_length=180)
    material_type = models.CharField(max_length=30, choices=MaterialTypeChoices.choices)
    file_format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    file = models.FileField(upload_to='exports/')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Exportação'
        verbose_name_plural = 'Exportações'

    def __str__(self):
        return f'{self.title} ({self.file_format})'
