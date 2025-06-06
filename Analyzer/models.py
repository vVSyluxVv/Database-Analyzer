from django.db import models

# Create your models here.

class Project(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class Table(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

class Column(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sample_data = models.TextField(null=True, blank=True)
    ai_description = models.TextField(null=True, blank=True)
    confidence = models.FloatField(default=0.0)
