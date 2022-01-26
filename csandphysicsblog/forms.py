from csandphysicsblog.models import Connect
from django import forms

class Contact(forms.ModelForm): # use forms.ModelForm when using a model as form else use forms.Form for just a normal form .
    class Meta:
        model = Connect  
        fields = "__all__"
    