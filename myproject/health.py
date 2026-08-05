from django.http import JsonResponse

from manyumbu10.phase8_services import readiness_report


def health(request):
    return JsonResponse({"status": "ok", "service": "manyumbu"})


def live(request):
    return JsonResponse({"status": "live"})


def ready(request):
    checks = readiness_report()
    status = 200 if checks.get("database") and checks.get("channel_layer") else 503
    return JsonResponse({"status": "ready" if status == 200 else "not_ready", "checks": checks}, status=status)
