from django.shortcuts import render

from .models import Project

# Create your views here.

def home(request):
    projects = Project.objects.all()
    return render(request, 'home.html', {'projects': projects})

def connect_db(request):
    return render(request, 'connect_db.html')

def select_table(request):
    return render(request, 'select_table.html')

def analyze(request):
    return render(request, 'analyze.html')
