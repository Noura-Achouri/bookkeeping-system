from django import forms
from .models import Record
from categories.models import MainCategory, SubCategory

class RecordForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=True
    )

    class Meta:
        model = Record
        fields = ['date', 'main_category', 'subcategory', 'transaction_type', 'amount', 'remarks', 'notes']
        widgets = {
            'remarks': forms.TextInput(attrs={'placeholder': 'Short description'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Anything worth remembering'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields['main_category'].queryset = MainCategory.objects.filter(user=user)
            self.fields['subcategory'].queryset = SubCategory.objects.filter(user=user)
            self.fields['subcategory'].required = False