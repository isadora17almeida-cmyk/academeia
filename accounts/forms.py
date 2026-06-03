from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from .models import Profile

COURSE_OBJECTIVES = {
    'direito': ['OAB', 'Concursos públicos', 'Provas da faculdade', 'Carreira acadêmica', 'Residência jurídica', 'Outros'],
    'medicina': ['Provas da faculdade', 'Residência médica', 'Internato', 'Revisão clínica', 'Outros'],
    'enfermagem': ['Provas da faculdade', 'Concursos', 'Residência multiprofissional', 'Prática clínica', 'Outros'],
    'psicologia': ['Provas da faculdade', 'Concursos', 'Clínica', 'Pesquisa acadêmica', 'Outros'],
    'administracao': ['Provas da faculdade', 'Concursos', 'Certificações', 'Mercado de trabalho', 'Outros'],
    'engenharia': ['Provas da faculdade', 'Concursos', 'Projetos', 'Certificações', 'Outros'],
    'pedagogia': ['Provas da faculdade', 'Concursos', 'Prática docente', 'Pesquisa acadêmica', 'Outros'],
    'contabilidade': ['Provas da faculdade', 'CRC', 'Concursos', 'Mercado de trabalho', 'Outros'],
    'geral': ['Provas', 'Concursos', 'Revisão geral', 'Aprendizado contínuo', 'Outros'],
    'outros': ['Objetivo personalizado'],
}


class NeonAuthenticationForm(AuthenticationForm):
    username = forms.CharField(label='Usuário ou e-mail', widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'seu usuário ou e-mail', 'autocomplete': 'username'
    }))
    password = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'sua senha', 'autocomplete': 'current-password'
    }))

    def clean(self):
        username = self.cleaned_data.get('username')
        if username and '@' in username:
            user = User.objects.filter(email__iexact=username).first()
            if user:
                self.cleaned_data['username'] = user.username
        return super().clean()


class RegisterForm(UserCreationForm):
    full_name = forms.CharField(label='Nome completo', max_length=180, widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Seu nome completo'
    }))
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={
        'class': 'form-control', 'placeholder': 'voce@email.com'
    }))
    study_area = forms.ChoiceField(label='Curso/área de estudo', choices=Profile.AREA_CHOICES, widget=forms.Select(attrs={
        'class': 'form-control'
    }))
    username = forms.CharField(label='Usuário', widget=forms.TextInput(attrs={
        'class': 'form-control', 'placeholder': 'Escolha um nome de usuário'
    }))
    password1 = forms.CharField(label='Senha', widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Crie uma senha segura'
    }))
    password2 = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput(attrs={
        'class': 'form-control', 'placeholder': 'Repita a senha'
    }))

    class Meta:
        model = User
        fields = ('full_name', 'email', 'study_area', 'username', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Já existe uma conta com este e-mail.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data['full_name'].strip()
        parts = full_name.split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
            user.profile.full_name = full_name
            user.profile.study_area = self.cleaned_data['study_area']
            user.profile.save()
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(label='Nome', max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(label='Sobrenome', max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(label='E-mail', widget=forms.EmailInput(attrs={'class': 'form-control'}))
    academic_goal = forms.ChoiceField(label='Objetivo acadêmico', required=False, choices=[], widget=forms.Select(attrs={'class': 'form-control', 'data-objective-select': '1'}))
    custom_goal = forms.CharField(label='Objetivo personalizado', required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: prova específica, concurso, certificação...'}))
    routine = forms.CharField(label='Rotina de estudos e trabalho', required=False, widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Ex.: trabalho 6h por dia, estudo 2h à noite, revisão aos sábados.'}))

    class Meta:
        model = Profile
        fields = ('full_name', 'study_area', 'college', 'objective', 'avatar')
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'study_area': forms.Select(attrs={'class': 'form-control', 'data-course-select': '1'}),
            'college': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da faculdade ou instituição'}),
            'objective': forms.HiddenInput(),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.fields['first_name'].initial = self.user.first_name
        self.fields['last_name'].initial = self.user.last_name
        self.fields['email'].initial = self.user.email
        area = (self.data.get('study_area') if self.is_bound else None) or self.instance.study_area or 'geral'
        choices = [(x, x) for x in COURSE_OBJECTIVES.get(area, COURSE_OBJECTIVES['geral'])]
        self.fields['academic_goal'].choices = [('', 'Selecione um objetivo')] + choices
        stored = self.instance.objective or ''
        self.fields['routine'].initial = ''
        if ' | Rotina: ' in stored:
            goal, routine = stored.split(' | Rotina: ', 1)
            self.fields['academic_goal'].initial = goal if goal in dict(choices) else 'Outros'
            self.fields['custom_goal'].initial = '' if goal in dict(choices) else goal
            self.fields['routine'].initial = routine
        else:
            self.fields['academic_goal'].initial = stored if stored in dict(choices) else ('Outros' if stored else '')
            self.fields['custom_goal'].initial = '' if stored in dict(choices) else stored

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data['first_name']
        self.user.last_name = self.cleaned_data['last_name']
        self.user.email = self.cleaned_data['email']
        selected_goal = self.cleaned_data.get('academic_goal') or ''
        custom_goal = self.cleaned_data.get('custom_goal') or ''
        routine = self.cleaned_data.get('routine') or ''
        final_goal = custom_goal if selected_goal in {'Outros', 'Objetivo personalizado'} or not selected_goal else selected_goal
        profile.objective = (final_goal + (f' | Rotina: {routine}' if routine else ''))[:220]
        if commit:
            self.user.save()
            profile.save()
        return profile
