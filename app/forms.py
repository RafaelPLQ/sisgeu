from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'icon']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Nome da categoria',
                'maxlength': '100',
                'required': True,
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '🎯',
                'maxlength': '10',
            }),
        }
        labels = {
            'name': 'Nome da Categoria',
            'icon': 'Emoji/Ícone',
        }
    
    def clean_icon(self):
        icon = self.cleaned_data.get('icon', '')
        if not icon:
            return '🎯'
        return icon

