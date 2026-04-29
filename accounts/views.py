from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from .forms import CadastroForm, PerfilForm, AlterarSenhaForm


def register(request):
    form = CadastroForm()

    if request.method == 'POST':
        form = CadastroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Conta criada com sucesso! Bem-vindo ao SISGEU.')
            return redirect('index')
        else:
            messages.error(request, 'Erro no cadastro. Verifique os dados e tente novamente.')

    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')

    error = None

    if request.method == 'POST':
        email = request.POST.get('username', '').strip()
        senha = request.POST.get('password', '')

        user = authenticate(request, username=email, password=senha)

        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
        else:
            # BUG CORRIGIDO: erro agora vai para a variável `error` que o template exibe
            error = 'E-mail ou senha incorretos.'

    return render(request, 'registration/login.html', {'error': error})


def logout_view(request):
    # BUG CORRIGIDO: só desloga via POST (CSRF protection)
    if request.method == 'POST':
        logout(request)
        return redirect('accounts:login')
    # GET: redireciona sem deslogar
    return redirect('index')


@login_required
def perfil_view(request):
    user = request.user

    # Garante que o perfil existe (segurança para usuários criados antes do signal)
    from .models import Perfil
    perfil, _ = Perfil.objects.get_or_create(usuario=user)

    # BUG CORRIGIDO: PerfilForm agora recebe os dados iniciais via initial= corretamente
    perfil_initial = {
        'nome': user.get_full_name() or user.username,
        'email': user.email,
        'data_nascimento': perfil.data_nascimento,
        'curso': perfil.curso or '',
        'instituicao': perfil.instituicao or '',
    }

    perfil_form = PerfilForm(user, initial=perfil_initial)
    senha_form = AlterarSenhaForm(user)

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'perfil':
            perfil_form = PerfilForm(user, request.POST)
            if perfil_form.is_valid():
                perfil_form.save()
                messages.success(request, 'Perfil atualizado com sucesso.')
                return redirect('accounts:perfil')
            else:
                messages.error(request, 'Verifique os dados e tente novamente.')

        elif acao == 'senha':
            senha_form = AlterarSenhaForm(user, request.POST)
            if senha_form.is_valid():
                senha_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, 'Senha alterada com sucesso.')
                return redirect('accounts:perfil')
            else:
                messages.error(request, 'Verifique os dados e tente novamente.')

    context = {
        'perfil_form': perfil_form,
        'senha_form': senha_form,
    }
    return render(request, 'registration/perfil.html', context)
