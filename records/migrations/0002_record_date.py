import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='record',
            name='date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
