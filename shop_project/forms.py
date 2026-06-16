from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):
    """
    Kept for potential future use - Django admin handles category
    creation for now via the inline parent field.
    """
    class Meta:
        model = Category
        fields = ['name', 'parent']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Category name'}),
        }
