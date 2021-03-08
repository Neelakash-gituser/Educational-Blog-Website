from django.urls import path
from . import views

urlpatterns = [path('',views.home,name='home'),
    path('topics',views.topic,name='topic'),
    path('details/<int:topic_id>/',views.details,name='details'),
    path('description/<int:study_id>/',views.description,name='description'),
    path('contactus',views.contact,name='contact'),
    path('publish',views.publish, name='publish'),
    path('about',views.about, name='about'),
]