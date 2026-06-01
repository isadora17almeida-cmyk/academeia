from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from studies.models import Flashcard, Folder, LibraryItem, Question, Summary


DIREITO = ['Direito Civil', 'Direito Penal', 'Direito Constitucional', 'Processo Civil', 'Processo Penal', 'Direito Administrativo', 'Direito do Trabalho']
MEDICINA = ['Anatomia', 'Histologia', 'Fisiologia', 'Patologia', 'Farmacologia', 'Clínica Médica', 'Pediatria', 'Cirurgia']


class Command(BaseCommand):
    help = 'Cria pastas e materiais de exemplo para demonstração do ACADEME.IA.'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Usuário que receberá os dados de exemplo.')

    def handle(self, *args, **options):
        username = options.get('username')
        if username:
            user = User.objects.filter(username=username).first()
        else:
            user = User.objects.filter(is_superuser=True).first() or User.objects.first()
        if not user:
            raise CommandError('Crie um usuário antes de rodar seed_demo.')

        for name in DIREITO:
            Folder.objects.get_or_create(user=user, name=name, defaults={'area': 'direito'})
        for name in MEDICINA:
            Folder.objects.get_or_create(user=user, name=name, defaults={'area': 'medicina'})

        summary, _ = Summary.objects.get_or_create(
            user=user,
            title='Obrigação de fazer no Direito Civil',
            defaults={
                'area': 'direito',
                'subject': 'Direito Civil',
                'source_type': 'assunto_digitado',
                'summary_type': 'completo',
                'level': 'intermediario',
                'input_text': 'Explique obrigação de fazer no Direito Civil.',
                'content': '# Obrigação de fazer\n\nConceito, fundamento legal, exemplos práticos, pegadinhas de prova e questões comentadas.',
            },
        )
        LibraryItem.objects.get_or_create(
            user=user,
            title=summary.title,
            material_type='resumo',
            defaults={'area': summary.area, 'subject': summary.subject, 'content': summary.content, 'object_id': summary.id},
        )

        q, _ = Question.objects.get_or_create(
            user=user,
            title='Pâncreas — Questão exemplo',
            defaults={
                'area': 'medicina',
                'subject': 'Anatomia',
                'statement': 'Sobre o pâncreas, assinale a alternativa correta.',
                'alternatives': ['A) Possui funções endócrinas e exócrinas.', 'B) Não possui relação com insulina.', 'C) É apenas órgão linfático.', 'D) Não possui vascularização relevante.'],
                'correct_answer': 'A',
                'explanation': 'O pâncreas participa da digestão e do controle glicêmico.',
            },
        )
        Flashcard.objects.get_or_create(
            user=user,
            question='Qual é a principal diferença entre função endócrina e exócrina do pâncreas?',
            defaults={
                'answer': 'A função endócrina secreta hormônios no sangue; a exócrina libera enzimas digestivas no duodeno.',
                'area': 'medicina',
                'subject': 'Anatomia',
            },
        )
        self.stdout.write(self.style.SUCCESS(f'Dados de exemplo criados para {user.username}.'))
