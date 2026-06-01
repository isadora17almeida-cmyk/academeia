from django.contrib import admin
from .models import Export, Exam, ExamAnswer, Flashcard, Folder, LibraryItem, Question, StudyPlan, Summary, Transcript


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'area', 'created_at')
    search_fields = ('name', 'user__username')
    list_filter = ('area',)


@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'area', 'subject', 'summary_type', 'created_at')
    search_fields = ('title', 'subject', 'content')
    list_filter = ('area', 'summary_type', 'level')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'area', 'subject', 'difficulty', 'question_type', 'created_at')
    search_fields = ('title', 'statement', 'subject')
    list_filter = ('area', 'difficulty', 'question_type')


@admin.register(Transcript)
class TranscriptAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'area', 'subject', 'status', 'created_at')
    search_fields = ('title', 'subject', 'raw_text', 'professor_text', 'summary_text', 'corrected_text')
    list_filter = ('area', 'status')


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ('question', 'user', 'area', 'subject', 'difficulty', 'hits', 'misses', 'review_date')
    search_fields = ('question', 'answer', 'subject')
    list_filter = ('area', 'difficulty')


class ExamAnswerInline(admin.TabularInline):
    model = ExamAnswer
    extra = 0


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'area', 'subject', 'difficulty', 'score', 'created_at')
    search_fields = ('title', 'subject')
    list_filter = ('area', 'difficulty')
    inlines = [ExamAnswerInline]


@admin.register(StudyPlan)
class StudyPlanAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'area', 'course', 'objective', 'progress', 'created_at')
    search_fields = ('title', 'course', 'subjects', 'content')
    list_filter = ('area', 'objective', 'difficulty')


@admin.register(LibraryItem)
class LibraryItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'material_type', 'area', 'subject', 'favorite', 'created_at')
    search_fields = ('title', 'subject', 'content')
    list_filter = ('material_type', 'area', 'favorite')


@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'material_type', 'file_format', 'created_at')
    list_filter = ('file_format', 'material_type')
