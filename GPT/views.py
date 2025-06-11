from django.shortcuts import render
from .chains import analyze_column

# Create your views here.

def ask_gpt(request):
    gpt_response = None

    if request.method == 'POST':
        column_name = request.POST.get('column_name')
        sample_values = request.POST.get('sample_values')
        gpt_response = analyze_column(column_name, sample_values)

    return render(request, 'gpt/result.html', {
        'gpt_response': gpt_response
    })