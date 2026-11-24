from django import forms
from .models import Post

class PostForm (forms.ModelForm):

    class Meta:

        model = Post
        fields = ["content","img"]

        widgets = {

            "content" : forms.Textarea(

                attrs={

                    "placeholder" : "Digite sua legenda aqui",
                    "rows" : 5
                }
            )
        }