from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('connect-db/', views.connect_db, name='connect_db'),
    path('select-table/', views.select_table, name='select_table'),
    path('analyze/', views.analyze, name='analyze'),
    path('view-table/', views.view_table, name='view_table'),
    path('download-analysis/', views.download_analysis, name='download_analysis'),
    path('erd/', views.database_summary_and_erd, name='database_erd'),
]
