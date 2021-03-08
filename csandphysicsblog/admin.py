from django.contrib import admin
from .models import Subject, Detail, Connect, Article

# Register your models here.
admin.site.register(Subject)
admin.site.register(Detail)
admin.site.register(Connect)
admin.site.register(Article)