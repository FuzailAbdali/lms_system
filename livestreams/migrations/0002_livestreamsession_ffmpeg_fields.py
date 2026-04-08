from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("livestreams", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="livestreamsession",
            name="ffmpeg_last_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ffmpeg_pid",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ffmpeg_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ffmpeg_status",
            field=models.CharField(
                choices=[
                    ("idle", "Idle"),
                    ("starting", "Starting"),
                    ("streaming", "Streaming"),
                    ("stopped", "Stopped"),
                    ("failed", "Failed"),
                ],
                default="idle",
                max_length=20,
            ),
        ),
    ]
