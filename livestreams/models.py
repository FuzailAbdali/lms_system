from django.conf import settings
from django.db import models
from django.utils import timezone


class LiveStreamSession(models.Model):
    class FFmpegStatus(models.TextChoices):
        IDLE = "idle", "Idle"
        STARTING = "starting", "Starting"
        STREAMING = "streaming", "Streaming"
        STOPPING = "stopping", "Stopping"
        STOPPED = "stopped", "Stopped"
        FAILED = "failed", "Failed"

    class PacketHealth(models.TextChoices):
        UNKNOWN = "unknown", "Unknown"
        HEALTHY = "healthy", "Healthy"
        STALE = "stale", "Stale"
        LOST = "lost", "Lost"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_stream_sessions",
        limit_choices_to={"role": "teacher"},
    )
    course = models.ForeignKey(
        "courses.Course",
        on_delete=models.CASCADE,
        related_name="live_stream_sessions",
    )
    title = models.CharField(max_length=255)
    youtube_stream_id = models.CharField(max_length=255, unique=True)
    youtube_broadcast_id = models.CharField(max_length=255, unique=True)
    stream_key = models.CharField(max_length=255)
    rtmp_url = models.URLField(max_length=500)
    watch_url = models.URLField(max_length=500)
    is_live = models.BooleanField(default=False)
    ffmpeg_status = models.CharField(
        max_length=20,
        choices=FFmpegStatus.choices,
        default=FFmpegStatus.IDLE,
    )
    ffmpeg_pid = models.PositiveIntegerField(null=True, blank=True)
    ffmpeg_started_at = models.DateTimeField(null=True, blank=True)
    ffmpeg_last_error = models.TextField(blank=True)
    ingest_pipe_path = models.CharField(max_length=500, blank=True)
    packet_health = models.CharField(
        max_length=20,
        choices=PacketHealth.choices,
        default=PacketHealth.UNKNOWN,
    )
    ingest_chunk_count = models.PositiveIntegerField(default=0)
    ingest_bytes_total = models.BigIntegerField(default=0)
    ingest_last_chunk_at = models.DateTimeField(null=True, blank=True)
    worker_heartbeat_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["teacher", "is_live"]),
            models.Index(fields=["course", "is_live"]),
            models.Index(fields=["youtube_stream_id"]),
            models.Index(fields=["youtube_broadcast_id"]),
        ]

    def __str__(self):
        return f"{self.course.title} - {self.title}"

    @property
    def replay_available(self):
        return bool(self.watch_url) and not self.is_live

    @property
    def packet_age_seconds(self):
        if not self.ingest_last_chunk_at:
            return None
        return max(0, int((timezone.now() - self.ingest_last_chunk_at).total_seconds()))
