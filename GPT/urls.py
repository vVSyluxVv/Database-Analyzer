from django.urls import path
from . import views

urlpatterns = [
    path('ask/', views.ask_gpt, name='ask_gpt'),
]