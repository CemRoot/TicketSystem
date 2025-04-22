from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticket_system', '0004_fix_suggested_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='ticket',
            name='gemini_message_count',
            field=models.IntegerField(default=0),
        ),
    ]
