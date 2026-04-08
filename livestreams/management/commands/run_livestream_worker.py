import threading
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.services import FFmpegStreamingError, FFmpegStreamingService
from livestreams.models import LiveStreamSession


class Command(BaseCommand):
    help = "Run the livestream worker that launches and supervises FFmpeg streaming processes."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_controllers = {}

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Livestream worker started."))
        while True:
            self._start_pending_sessions()
            self._refresh_active_sessions()
            time.sleep(settings.LIVESTREAM_WORKER_POLL_INTERVAL)

    def _start_pending_sessions(self):
        pending_sessions = LiveStreamSession.objects.filter(
            ffmpeg_status=LiveStreamSession.FFmpegStatus.STARTING
        ).order_by("created_at")

        for session in pending_sessions:
            if session.pk in self.active_controllers:
                continue
            service = FFmpegStreamingService(session)
            try:
                process, log_handle = service.launch_worker_process()
                stop_event = threading.Event()
                server_socket, server_thread = service.start_ingest_socket_server(process, stop_event)
            except FFmpegStreamingError as exc:
                self.stderr.write(f"Session {session.pk} failed to start: {exc}")
                continue

            self.active_controllers[session.pk] = {
                "process": process,
                "log_handle": log_handle,
                "stop_event": stop_event,
                "server_socket": server_socket,
                "server_thread": server_thread,
            }
            self.stdout.write(f"Session {session.pk} streaming with PID {process.pid}.")
            self._watch_process(session.pk, process, log_handle, stop_event, server_socket)

    def _refresh_active_sessions(self):
        active_sessions = LiveStreamSession.objects.filter(
            ffmpeg_status__in=[
                LiveStreamSession.FFmpegStatus.STREAMING,
                LiveStreamSession.FFmpegStatus.STOPPING,
            ]
        )

        for session in active_sessions:
            service = FFmpegStreamingService(session)
            service.touch_worker_heartbeat()
            service.refresh_packet_health()

    def _watch_process(self, session_pk, process, log_handle, stop_event, server_socket):
        def _monitor():
            process.wait()
            stop_event.set()
            try:
                server_socket.close()
            except OSError:
                pass
            if not log_handle.closed:
                log_handle.close()
            self.active_controllers.pop(session_pk, None)

            try:
                session = LiveStreamSession.objects.get(pk=session_pk)
            except LiveStreamSession.DoesNotExist:
                return

            service = FFmpegStreamingService(session)
            if process.returncode == 0 and session.ffmpeg_status == LiveStreamSession.FFmpegStatus.STOPPED:
                service.refresh_packet_health()
                return

            if process.returncode == 0 and session.ffmpeg_status == LiveStreamSession.FFmpegStatus.STREAMING:
                session.ffmpeg_status = LiveStreamSession.FFmpegStatus.STOPPED
                session.is_live = False
                if not session.ended_at:
                    session.ended_at = timezone.now()
                session.save(update_fields=["ffmpeg_status", "is_live", "ended_at", "updated_at"])
                return

            failure_reason = service._read_last_log_line(service._build_log_path()) or (
                f"FFmpeg exited with code {process.returncode}."
            )
            service.refresh_packet_health(force_failed=True, error_message=failure_reason)

        monitor_thread = threading.Thread(target=_monitor, daemon=True)
        monitor_thread.start()
