# Generated by Django 5.2 on 2025-04-30 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tablelogic', '0002_alter_practicalassignment_teacher2'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='timetableentry',
            name='duration',
        ),
        migrations.AlterField(
            model_name='timetableentry',
            name='day',
            field=models.CharField(choices=[('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday')], max_length=10),
        ),
    ]
