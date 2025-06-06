from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('connect-db/', views.connect_db, name='connect_db'),
    path('select-table/', views.select_table, name='select_table'),
    path('analyze/', views.analyze, name='analyze'),
]
