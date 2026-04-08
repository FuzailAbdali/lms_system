from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("livestreams", "0002_livestreamsession_ffmpeg_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="livestreamsession",
            name="ended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ingest_bytes_total",
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ingest_chunk_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ingest_last_chunk_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="ingest_pipe_path",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="packet_health",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("healthy", "Healthy"),
                    ("stale", "Stale"),
                    ("lost", "Lost"),
                ],
                default="unknown",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="livestreamsession",
            name="worker_heartbeat_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="livestreamsession",
            name="ffmpeg_status",
            field=models.CharField(
                choices=[
                    ("idle", "Idle"),
                    ("starting", "Starting"),
                    ("streaming", "Streaming"),
                    ("stopping", "Stopping"),
                    ("stopped", "Stopped"),
                    ("failed", "Failed"),
                ],
                default="idle",
                max_length=20,
            ),
        ),
    ]
