from django.urls import path
from . import views

app_name = 'studies'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('resumos/', views.generate_summary, name='generate_summary'),
    path('questoes/', views.create_questions, name='create_questions'),
    path('transcricoes/', views.transcriptions, name='transcriptions'),
    path('transcricoes/<int:pk>/', views.transcript_detail, name='transcript_detail'),
    path('transcricoes/<int:pk>/<str:action>/', views.transcript_action, name='transcript_action'),
    path('biblioteca/', views.library, name='library'),
    path('biblioteca/<int:pk>/', views.library_detail, name='library_detail'),
    path('biblioteca/<int:pk>/delete/', views.library_delete, name='library_delete'),
    path('biblioteca/<int:pk>/favorite/', views.library_toggle_favorite, name='library_toggle_favorite'),
    path('biblioteca/<int:pk>/export/<str:file_format>/', views.export_library_item, name='export_library_item'),
    path('flashcards/', views.flashcards, name='flashcards'),
    path('flashcards/<int:pk>/<str:result>/', views.review_flashcard, name='review_flashcard'),
    path('simulados/', views.simulations, name='simulations'),
    path('simulados/<int:pk>/', views.exam_detail, name='exam_detail'),
    path('plano-de-estudos/', views.study_plan, name='study_plan'),
]
