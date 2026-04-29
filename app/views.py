from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed


class IndexView(LoginRequiredMixin, View):
    # LOGIN_URL já definido em settings.py como /accounts/login/
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        context = {}
        # BUG CORRIGIDO: renderiza o dashboard, não o base.html diretamente
        return render(request, 'pages/dashboard.html', context)

    def post(self, request, *args, **kwargs):
        return HttpResponseNotAllowed(['GET'])
