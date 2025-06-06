from django.db import models

# Create your models here.

class Project(models.Model):
    db_name = models.CharField(max_length=255, default="")
    table_count = models.IntegerField(default=0)
    column_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.db_name

class Table(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

class Column(models.Model):
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    sample_data = models.TextField(null=True, blank=True)
    ai_description = models.TextField(null=True, blank=True)
    confidence = models.FloatField(default=0.0)
