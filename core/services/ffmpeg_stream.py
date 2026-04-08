import errno
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

from django.conf import settings
from django.utils import timezone


class FFmpegStreamingError(Exception):
    pass


class FFmpegStreamingService:
    def __init__(self, session):
        self.session = session

    def queue_browser_stream(self, stream_key, rtmp_url, input_format=None):
        self.refresh_packet_health()
        if self.session.ffmpeg_status in {
            self.session.FFmpegStatus.STARTING,
            self.session.FFmpegStatus.STREAMING,
        }:
            raise FFmpegStreamingError("This live session is already starting or streaming.")

        pipe_path = self._build_pipe_path()
        pipe_path.parent.mkdir(parents=True, exist_ok=True)
        if pipe_path.exists():
            pipe_path.unlink()

        self.session.ingest_pipe_path = str(pipe_path)
        self.session.ffmpeg_status = self.session.FFmpegStatus.STARTING
        self.session.ffmpeg_pid = None
        self.session.ffmpeg_started_at = None
        self.session.ffmpeg_last_error = ""
        self.session.ingest_chunk_count = 0
        self.session.ingest_bytes_total = 0
        self.session.ingest_last_chunk_at = None
        self.session.packet_health = self.session.PacketHealth.UNKNOWN
        self.session.ended_at = None
        self.session.is_live = True
        self.session.save(
            update_fields=[
                "ingest_pipe_path",
                "ffmpeg_status",
                "ffmpeg_pid",
                "ffmpeg_started_at",
                "ffmpeg_last_error",
                "ingest_chunk_count",
                "ingest_bytes_total",
                "ingest_last_chunk_at",
                "packet_health",
                "ended_at",
                "is_live",
                "updated_at",
            ]
        )
        worker_pid = self.ensure_worker_running()
        return str(pipe_path), input_format or settings.FFMPEG_BROWSER_INPUT_FORMAT, worker_pid

    @staticmethod
    def ensure_worker_running():
        pid_file = Path(settings.LIVESTREAM_WORKER_PID_FILE)
        log_file = Path(settings.LIVESTREAM_WORKER_LOG_FILE)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        existing_pid = FFmpegStreamingService._read_worker_pid(pid_file)
        if existing_pid and FFmpegStreamingService._process_is_running(existing_pid):
            return existing_pid

        python_bin = settings.LIVESTREAM_WORKER_PYTHON or sys.executable or "python3"
        with log_file.open("ab") as log_handle:
            process = subprocess.Popen(
                [python_bin, "manage.py", "run_livestream_worker"],
                cwd=str(settings.BASE_DIR),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        pid_file.write_text(str(process.pid))
        return process.pid

    def launch_worker_process(self, input_format=None):
        if not self.session.ingest_pipe_path:
            raise FFmpegStreamingError("No ingest pipe is configured for this live session.")

        pipe_path = Path(self.session.ingest_pipe_path)
        pipe_path.parent.mkdir(parents=True, exist_ok=True)

        output_url = self._build_output_url(self.session.stream_key, self.session.rtmp_url)
        log_path = self._build_log_path()
        command = self._build_browser_ffmpeg_command(
            output_url=output_url,
            input_format=input_format or settings.FFMPEG_BROWSER_INPUT_FORMAT,
        )

        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("wb")

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            log_handle.close()
            self._mark_failed(f"FFmpeg binary was not found: {settings.FFMPEG_BINARY}")
            raise FFmpegStreamingError("FFmpeg is not installed or the configured binary path is invalid.") from exc
        except Exception as exc:
            log_handle.close()
            self._mark_failed(str(exc))
            raise FFmpegStreamingError(f"Could not start FFmpeg: {exc}") from exc

        time.sleep(1)
        if process.poll() is not None:
            log_handle.close()
            failure_reason = self._read_last_log_line(log_path) or "FFmpeg exited immediately after startup."
            self._mark_failed(failure_reason)
            raise FFmpegStreamingError(f"FFmpeg could not start streaming: {failure_reason}")

        self.session.ffmpeg_pid = process.pid
        self.session.ffmpeg_status = self.session.FFmpegStatus.STREAMING
        self.session.ffmpeg_started_at = timezone.now()
        self.session.worker_heartbeat_at = timezone.now()
        self.session.ffmpeg_last_error = ""
        self.session.save(
            update_fields=[
                "ffmpeg_pid",
                "ffmpeg_status",
                "ffmpeg_started_at",
                "worker_heartbeat_at",
                "ffmpeg_last_error",
                "updated_at",
            ]
        )
        return process, log_handle

    def upload_chunk(self, chunk_bytes):
        self.refresh_packet_health()
        if self.session.ffmpeg_status not in {
            self.session.FFmpegStatus.STARTING,
            self.session.FFmpegStatus.STREAMING,
        }:
            raise FFmpegStreamingError("No active worker stream is ready to receive browser media.")

        if not self.session.ingest_pipe_path:
            raise FFmpegStreamingError("The ingest pipe is not configured for this session.")

        if not chunk_bytes:
            raise FFmpegStreamingError("Received an empty media chunk.")

        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                client.connect(self.session.ingest_pipe_path)
                client.sendall(chunk_bytes)
        except OSError as exc:
            if exc.errno in {errno.ENOENT, errno.ECONNREFUSED}:
                raise FFmpegStreamingError("The stream worker is not ready to receive media yet.") from exc
            raise FFmpegStreamingError(f"Could not write media chunk to ingest pipe: {exc}") from exc

        self.session.ingest_chunk_count += 1
        self.session.ingest_bytes_total += len(chunk_bytes)
        self.session.ingest_last_chunk_at = timezone.now()
        self.session.packet_health = self.session.PacketHealth.HEALTHY
        self.session.save(
            update_fields=[
                "ingest_chunk_count",
                "ingest_bytes_total",
                "ingest_last_chunk_at",
                "packet_health",
                "updated_at",
            ]
        )
        return len(chunk_bytes)

    def stop_stream(self):
        self.refresh_packet_health()
        pid = self.session.ffmpeg_pid
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

        self.session.ffmpeg_pid = None
        self.session.ffmpeg_status = self.session.FFmpegStatus.STOPPED
        self.session.packet_health = self.session.PacketHealth.UNKNOWN
        self.session.is_live = False
        self.session.ended_at = timezone.now()
        self.session.save(
            update_fields=[
                "ffmpeg_pid",
                "ffmpeg_status",
                "packet_health",
                "is_live",
                "ended_at",
                "updated_at",
            ]
        )
        self._remove_ingest_pipe()
        return bool(pid)

    def refresh_packet_health(self, force_failed=False, error_message=""):
        if force_failed:
            self.session.ffmpeg_pid = None
            self.session.ffmpeg_status = self.session.FFmpegStatus.FAILED
            self.session.packet_health = self.session.PacketHealth.LOST
            self.session.ffmpeg_last_error = error_message or self.session.ffmpeg_last_error
            self.session.is_live = False
            if not self.session.ended_at:
                self.session.ended_at = timezone.now()
            self.session.save(
                update_fields=[
                    "ffmpeg_pid",
                    "ffmpeg_status",
                    "packet_health",
                    "ffmpeg_last_error",
                    "is_live",
                    "ended_at",
                    "updated_at",
                ]
            )
            return self.session.packet_health

        status_changed = False
        if self.session.ffmpeg_pid and not self._process_is_running(self.session.ffmpeg_pid):
            self.session.ffmpeg_pid = None
            if self.session.ffmpeg_status in {self.session.FFmpegStatus.STARTING, self.session.FFmpegStatus.STREAMING}:
                self.session.ffmpeg_status = self.session.FFmpegStatus.STOPPED
            self.session.is_live = False
            if not self.session.ended_at:
                self.session.ended_at = timezone.now()
            status_changed = True

        packet_health = self.session.PacketHealth.UNKNOWN
        if self.session.ffmpeg_status == self.session.FFmpegStatus.STREAMING:
            if not self.session.ingest_last_chunk_at:
                packet_health = self.session.PacketHealth.STALE
            else:
                age = (timezone.now() - self.session.ingest_last_chunk_at).total_seconds()
                if age <= settings.LIVESTREAM_PACKET_HEALTHY_SECONDS:
                    packet_health = self.session.PacketHealth.HEALTHY
                elif age <= settings.LIVESTREAM_PACKET_STALE_SECONDS:
                    packet_health = self.session.PacketHealth.STALE
                else:
                    packet_health = self.session.PacketHealth.LOST
        self.session.packet_health = packet_health

        if status_changed:
            self.session.save(
                update_fields=[
                    "ffmpeg_pid",
                    "ffmpeg_status",
                    "packet_health",
                    "is_live",
                    "ended_at",
                    "updated_at",
                ]
            )
        return packet_health

    def sync_process_state(self):
        return self.refresh_packet_health()

    def touch_worker_heartbeat(self):
        self.session.worker_heartbeat_at = timezone.now()
        self.session.save(update_fields=["worker_heartbeat_at", "updated_at"])

    def start_ingest_socket_server(self, process, stop_event):
        if not self.session.ingest_pipe_path:
            raise FFmpegStreamingError("No ingest socket path is configured for this live session.")

        socket_path = Path(self.session.ingest_pipe_path)
        if socket_path.exists():
            socket_path.unlink()

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen()
        server.settimeout(1.0)

        def _serve():
            while not stop_event.is_set():
                try:
                    conn, _ = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                with conn:
                    while True:
                        data = conn.recv(65536)
                        if not data:
                            break
                        try:
                            if process.stdin:
                                process.stdin.write(data)
                                process.stdin.flush()
                        except (BrokenPipeError, OSError):
                            stop_event.set()
                            break

            try:
                server.close()
            except OSError:
                pass

        thread = threading.Thread(target=_serve, daemon=True)
        thread.start()
        return server, thread

    def _mark_failed(self, error_message):
        self.session.ffmpeg_pid = None
        self.session.ffmpeg_status = self.session.FFmpegStatus.FAILED
        self.session.packet_health = self.session.PacketHealth.LOST
        self.session.ffmpeg_last_error = error_message
        self.session.is_live = False
        if not self.session.ended_at:
            self.session.ended_at = timezone.now()
        self.session.save(
            update_fields=[
                "ffmpeg_pid",
                "ffmpeg_status",
                "packet_health",
                "ffmpeg_last_error",
                "is_live",
                "ended_at",
                "updated_at",
            ]
        )
        self._remove_ingest_pipe()

    def _remove_ingest_pipe(self):
        if self.session.ingest_pipe_path:
            pipe_path = Path(self.session.ingest_pipe_path)
            if pipe_path.exists():
                pipe_path.unlink()
            self.session.ingest_pipe_path = ""
            self.session.save(update_fields=["ingest_pipe_path", "updated_at"])

    @staticmethod
    def _process_is_running(pid):
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _read_worker_pid(pid_file):
        try:
            raw = pid_file.read_text().strip()
        except OSError:
            return None
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    @staticmethod
    def _build_output_url(stream_key, rtmp_url):
        if not stream_key or not str(stream_key).strip():
            raise FFmpegStreamingError("A YouTube stream key is required.")
        if not rtmp_url or not str(rtmp_url).strip():
            raise FFmpegStreamingError("A YouTube RTMP URL is required.")

        normalized_rtmp_url = str(rtmp_url).rstrip("/")
        normalized_stream_key = str(stream_key).lstrip("/")
        return f"{normalized_rtmp_url}/{normalized_stream_key}"

    def _build_pipe_path(self):
        return Path(settings.LIVESTREAM_PIPE_DIR) / f"session_{self.session.pk}.fifo"

    def _build_log_path(self):
        return Path(settings.FFMPEG_LOG_DIR) / f"live_session_{self.session.pk}.log"

    @staticmethod
    def _read_last_log_line(log_path):
        try:
            lines = log_path.read_text(errors="ignore").splitlines()
        except OSError:
            return ""

        for line in reversed(lines):
            cleaned = line.strip()
            if cleaned:
                return cleaned
        return ""

    @staticmethod
    def _build_browser_ffmpeg_command(output_url, input_format):
        return [
            settings.FFMPEG_BINARY,
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "+genpts",
            "-thread_queue_size",
            "1024",
            "-f",
            input_format,
            "-i",
            "pipe:0",
            "-vcodec",
            "libx264",
            "-preset",
            settings.FFMPEG_VIDEO_PRESET,
            "-pix_fmt",
            "yuv420p",
            "-g",
            str(settings.FFMPEG_GOP_SIZE),
            "-r",
            str(settings.FFMPEG_OUTPUT_FRAME_RATE),
            "-b:v",
            settings.FFMPEG_VIDEO_BITRATE,
            "-maxrate",
            settings.FFMPEG_MAX_VIDEO_BITRATE,
            "-bufsize",
            settings.FFMPEG_BUFFER_SIZE,
            "-acodec",
            "aac",
            "-ar",
            "44100",
            "-b:a",
            settings.FFMPEG_AUDIO_BITRATE,
            "-f",
            "flv",
            output_url,
        ]
