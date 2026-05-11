import requests
import json

# Teste básico da API
url = 'http://localhost:8000/orcamento/add-category/'
data = {
    'name': 'Teste Categoria',
    'icon': '🎯',
    'csrfmiddlewaretoken': 'dummy_token'  # Este será rejeitado, mas vamos ver se a view é chamada
}

try:
    response = requests.post(url, data=data)
    print(f'Status: {response.status_code}')
    print(f'Response: {response.text}')
except Exception as e:
    print(f'Erro: {e}')