# Generated by Django 5.2 on 2025-04-30 17:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tablelogic', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='practicalassignment',
            name='teacher2',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='practical_teacher2', to='tablelogic.teacher'),
        ),
    ]
