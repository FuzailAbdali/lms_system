import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from courses.models import Course
from users.decorators import role_required
from users.models import User

from core.services import (
    FFmpegStreamingError,
    FFmpegStreamingService,
    complete_youtube_authorization,
    create_youtube_live_broadcast,
    create_youtube_live_stream,
    get_youtube_authorization_url,
    has_valid_youtube_credentials,
)

from .forms import StartLiveClassForm
from .models import LiveStreamSession


def _start_live_session(request, course, title, description):
    stream_data = create_youtube_live_stream(
        title=title,
        description=description,
    )
    broadcast_data = create_youtube_live_broadcast(
        title=title,
        description=description,
        start_time=timezone.now(),
        stream_id=stream_data["stream_id"],
    )

    session = LiveStreamSession.objects.create(
        teacher=request.user,
        course=course,
        title=title,
        youtube_stream_id=stream_data["stream_id"],
        youtube_broadcast_id=broadcast_data["broadcast_id"],
        stream_key=stream_data["stream_key"],
        rtmp_url=stream_data["ingestion_address"],
        watch_url=broadcast_data["watch_url"],
        is_live=True,
    )
    return session


@role_required(User.Role.TEACHER)
def live_class_start(request):
    form = StartLiveClassForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.cleaned_data["course"]
        title = form.cleaned_data["title"]
        description = form.cleaned_data["description"]

        if not has_valid_youtube_credentials():
            request.session["youtube_pending_live_class"] = {
                "course_id": course.pk,
                "title": title,
                "description": description,
            }
            request.session["youtube_post_auth_redirect"] = "live_class_start"
            return redirect("youtube_auth_start")

        try:
            session = _start_live_session(request, course, title, description)
        except Exception as exc:
            messages.error(request, f"Could not start the live class: {exc}")
        else:
            messages.success(request, "Live class started successfully.")
            return redirect("live_class_studio", pk=session.pk)

    return render(
        request,
        "livestreams/live_class_form.html",
        {
            "title": "Start Live Class",
            "form": form,
        },
    )


@role_required(User.Role.TEACHER)
def youtube_auth_start(request):
    oauth_data = get_youtube_authorization_url()
    request.session["youtube_oauth_state"] = oauth_data["state"]
    request.session["youtube_oauth_code_verifier"] = oauth_data.get("code_verifier")
    request.session.modified = True
    return redirect(oauth_data["authorization_url"])


@role_required(User.Role.TEACHER)
def youtube_auth_callback(request):
    state = request.session.get("youtube_oauth_state")
    code_verifier = request.session.get("youtube_oauth_code_verifier")
    if not state:
        messages.error(request, "Missing YouTube OAuth state. Please try again.")
        return redirect("live_class_start")

    returned_state = request.GET.get("state")
    if returned_state and returned_state != state:
        request.session.pop("youtube_oauth_state", None)
        request.session.pop("youtube_oauth_code_verifier", None)
        messages.error(request, "YouTube authentication state did not match. Please try again.")
        return redirect("live_class_start")

    try:
        complete_youtube_authorization(
            request.build_absolute_uri(),
            state,
            code_verifier=code_verifier,
        )
    except Exception as exc:
        messages.error(request, f"Could not connect YouTube account: {exc}")
        return redirect("live_class_start")
    finally:
        request.session.pop("youtube_oauth_state", None)
        request.session.pop("youtube_oauth_code_verifier", None)

    pending_live_class = request.session.pop("youtube_pending_live_class", None)
    post_auth_redirect = request.session.pop("youtube_post_auth_redirect", "live_class_start")
    if pending_live_class:
        try:
            course = Course.objects.get(pk=pending_live_class["course_id"], teacher=request.user)
            session = _start_live_session(
                request,
                course,
                pending_live_class["title"],
                pending_live_class.get("description", ""),
            )
        except Course.DoesNotExist:
            messages.error(request, "The selected course is no longer available for this teacher.")
            return redirect(post_auth_redirect)
        except Exception as exc:
            messages.error(request, f"YouTube connected, but live class could not be started: {exc}")
            return redirect(post_auth_redirect)
        else:
            messages.success(request, "YouTube connected and live class started successfully.")
            return redirect("live_class_studio", pk=session.pk)

    messages.success(request, "YouTube account connected successfully.")
    return redirect(post_auth_redirect)


@role_required(User.Role.TEACHER)
def live_class_detail(request, pk):
    session = get_object_or_404(
        LiveStreamSession.objects.select_related("course", "teacher"),
        pk=pk,
        teacher=request.user,
    )
    return render(
        request,
        "livestreams/live_class_detail.html",
        {
            "title": session.title,
            "session": session,
            "recent_history": (
                LiveStreamSession.objects.filter(teacher=request.user)
                .exclude(pk=session.pk)
                .order_by("-created_at")[:5]
            ),
        },
    )


@role_required(User.Role.TEACHER)
def live_class_studio(request, pk):
    session = get_object_or_404(
        LiveStreamSession.objects.select_related("course", "teacher"),
        pk=pk,
        teacher=request.user,
    )
    FFmpegStreamingService(session).sync_process_state()
    session.refresh_from_db()
    return render(
        request,
        "livestreams/live_class_studio.html",
        {
            "title": f"{session.title} Studio",
            "session": session,
            "ffmpeg_status": session.ffmpeg_status,
            "ffmpeg_last_error": session.ffmpeg_last_error,
        },
    )


@role_required(User.Role.TEACHER)
def live_class_stream_start(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    session = get_object_or_404(LiveStreamSession, pk=pk, teacher=request.user)

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    stream_key = payload.get("stream_key") or session.stream_key
    rtmp_url = payload.get("rtmp_url") or session.rtmp_url
    input_format = payload.get("input_format")

    try:
        service = FFmpegStreamingService(session)
        pipe_path, selected_format, worker_pid = service.queue_browser_stream(
            stream_key=stream_key,
            rtmp_url=rtmp_url,
            input_format=input_format,
        )
    except FFmpegStreamingError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "status": session.FFmpegStatus.STARTING,
            "pipe_path": pipe_path,
            "input_format": selected_format,
            "worker_pid": worker_pid,
            "stream_key": stream_key,
            "rtmp_url": rtmp_url,
        }
    )


@csrf_exempt
@role_required(User.Role.TEACHER)
def live_class_stream_upload(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    session = get_object_or_404(LiveStreamSession, pk=pk, teacher=request.user)
    chunk = request.body

    try:
        bytes_written = FFmpegStreamingService(session).upload_chunk(chunk)
    except FFmpegStreamingError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "status": session.FFmpegStatus.STREAMING,
            "bytes_written": bytes_written,
        }
    )


@role_required(User.Role.TEACHER)
def live_class_stream_status(request, pk):
    session = get_object_or_404(LiveStreamSession, pk=pk, teacher=request.user)
    service = FFmpegStreamingService(session)
    service.refresh_packet_health()
    session.refresh_from_db()
    return JsonResponse(
        {
            "status": session.ffmpeg_status,
            "packet_health": session.packet_health,
            "ingest_chunk_count": session.ingest_chunk_count,
            "ingest_bytes_total": session.ingest_bytes_total,
            "packet_age_seconds": session.packet_age_seconds,
            "ffmpeg_last_error": session.ffmpeg_last_error,
            "worker_heartbeat_at": session.worker_heartbeat_at.isoformat() if session.worker_heartbeat_at else None,
            "is_live": session.is_live,
        }
    )


@role_required(User.Role.TEACHER)
def live_class_stream_stop(request, pk):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed."}, status=405)

    session = get_object_or_404(LiveStreamSession, pk=pk, teacher=request.user)
    service = FFmpegStreamingService(session)
    stopped = service.stop_stream()
    return JsonResponse(
        {
            "status": session.FFmpegStatus.STOPPED,
            "stopped": stopped,
        }
    )


@role_required(User.Role.TEACHER)
def live_class_history(request):
    sessions = LiveStreamSession.objects.filter(teacher=request.user).select_related("course").order_by("-created_at")
    return render(
        request,
        "livestreams/live_class_history.html",
        {
            "title": "Live Session History",
            "sessions": sessions,
        },
    )


@role_required(User.Role.TEACHER)
def live_class_delete(request, pk):
    if request.method != "POST":
        return redirect("live_class_history")

    session = get_object_or_404(LiveStreamSession, pk=pk, teacher=request.user)
    if session.ffmpeg_status in {
        session.FFmpegStatus.STARTING,
        session.FFmpegStatus.STREAMING,
    }:
        FFmpegStreamingService(session).stop_stream()
    session.delete()
    messages.success(request, "Live session history entry deleted.")
    return redirect("live_class_history")


@role_required(User.Role.STUDENT)
def student_live_class_watch(request, course_pk):
    course = get_object_or_404(Course.objects.select_related("teacher"), pk=course_pk)
    session = (
        LiveStreamSession.objects.select_related("course", "teacher")
        .filter(course=course, is_live=True)
        .order_by("-created_at")
        .first()
    )
    context = {
        "title": f"{course.title} Live Class",
        "course": course,
        "session": session,
    }
    return render(request, "livestreams/student_live_class_watch.html", context)
