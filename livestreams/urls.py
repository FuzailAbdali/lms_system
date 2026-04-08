from django.urls import path

from .views import (
    live_class_delete,
    live_class_detail,
    live_class_history,
    live_class_start,
    live_class_stream_start,
    live_class_stream_status,
    live_class_stream_stop,
    live_class_stream_upload,
    live_class_studio,
    student_live_class_watch,
)

urlpatterns = [
    path("history/", live_class_history, name="live_class_history"),
    path("start/", live_class_start, name="live_class_start"),
    path("<int:pk>/", live_class_detail, name="live_class_detail"),
    path("<int:pk>/delete/", live_class_delete, name="live_class_delete"),
    path("<int:pk>/studio/", live_class_studio, name="live_class_studio"),
    path("<int:pk>/studio/start-stream/", live_class_stream_start, name="live_class_stream_start"),
    path("<int:pk>/studio/status/", live_class_stream_status, name="live_class_stream_status"),
    path("<int:pk>/studio/upload-chunk/", live_class_stream_upload, name="live_class_stream_upload"),
    path("<int:pk>/studio/stop-stream/", live_class_stream_stop, name="live_class_stream_stop"),
    path("courses/<int:course_pk>/watch/", student_live_class_watch, name="student_live_class_watch"),
]
