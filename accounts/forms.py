from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Perfil


class CadastroForm(forms.Form):
    nome = forms.CharField(
        max_length=150,
        label='Nome completo',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Seu nome'}),
    )
    data_nascimento = forms.DateField(
        label='Data de nascimento',
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'seu@email.com'}),
    )
    senha = forms.CharField(
        label='Senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'}),
    )
    curso = forms.CharField(
        max_length=150,
        label='Curso',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Engenharia de Software'}),
    )
    instituicao = forms.CharField(
        max_length=200,
        label='Instituição',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: UFMG'}),
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail já está cadastrado.')
        return email

    def clean_senha(self):
        # BUG CORRIGIDO: valida a senha com as regras do Django (CommonPassword, etc.)
        senha = self.cleaned_data.get('senha')
        if senha:
            try:
                validate_password(senha)
            except forms.ValidationError as e:
                raise forms.ValidationError(e.messages)
        return senha

    def save(self):
        data = self.cleaned_data
        nome_parts = data['nome'].strip().split(' ', 1)
        first_name = nome_parts[0]
        last_name = nome_parts[1] if len(nome_parts) > 1 else ''

        user = User.objects.create_user(
            username=data['email'],   # usa e-mail como username
            email=data['email'],
            password=data['senha'],
            first_name=first_name,
            last_name=last_name,
        )

        # O signal já cria o Perfil; apenas atualiza os campos extras
        user.perfil.data_nascimento = data['data_nascimento']
        user.perfil.curso = data['curso']
        user.perfil.instituicao = data['instituicao']
        user.perfil.save()

        return user


class PerfilForm(forms.Form):
    nome = forms.CharField(
        max_length=150,
        label='Nome completo',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Seu nome'}),
    )
    email = forms.EmailField(
        label='E-mail',
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'seu@email.com'}),
    )
    data_nascimento = forms.DateField(
        label='Data de nascimento',
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
    )
    curso = forms.CharField(
        max_length=150,
        label='Curso',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: Engenharia de Software'}),
    )
    instituicao = forms.CharField(
        max_length=200,
        label='Instituição',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Ex: UFMG'}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError('Este e-mail já está em uso por outra conta.')
        return email

    def save(self):
        data = self.cleaned_data
        user = self.user

        nome_parts = data['nome'].strip().split(' ', 1)
        user.first_name = nome_parts[0]
        user.last_name = nome_parts[1] if len(nome_parts) > 1 else ''
        user.email = data['email']
        user.username = data['email']  # mantém username = email
        user.save()

        perfil = user.perfil
        perfil.data_nascimento = data.get('data_nascimento')
        perfil.curso = data.get('curso', '')
        perfil.instituicao = data.get('instituicao', '')
        perfil.save()


class AlterarSenhaForm(forms.Form):
    senha_atual = forms.CharField(
        label='Senha atual',
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'}),
    )
    nova_senha = forms.CharField(
        label='Nova senha',
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'}),
    )
    confirmar_senha = forms.CharField(
        label='Confirmar nova senha',
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': '••••••••'}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_senha_atual(self):
        senha = self.cleaned_data.get('senha_atual')
        if not self.user.check_password(senha):
            raise forms.ValidationError('Senha atual incorreta.')
        return senha

    def clean(self):
        cleaned = super().clean()
        nova = cleaned.get('nova_senha')
        confirmar = cleaned.get('confirmar_senha')
        if nova and confirmar and nova != confirmar:
            self.add_error('confirmar_senha', 'As senhas não coincidem.')
        if nova:
            try:
                validate_password(nova, self.user)
            except forms.ValidationError as e:
                self.add_error('nova_senha', e)
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data['nova_senha'])
        self.user.save()
