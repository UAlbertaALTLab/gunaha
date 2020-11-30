# Generated by Django 2.2.15 on 2020-11-30 20:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('morphodict', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnespotDuplicate',
            fields=[
                ('entry_id', models.CharField(max_length=7, primary_key=True, serialize=False)),
                ('duplicate_of', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='morphodict.Head')),
            ],
        ),
    ]
