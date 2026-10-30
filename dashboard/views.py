
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Analisis



@require_GET
def obtener_resumen(request):
    resumen = {
        "proyecto": "FailNet",
        "estado": "operativo",
        "total_analisis": Analisis.objects.count(),
        "sofi": Analisis.objects.filter(
            tipo=Analisis.Tipo.SOFI
        ).count(),
        "digital_twin": Analisis.objects.filter(
            tipo=Analisis.Tipo.DIGITAL_TWIN
        ).count(),
        "pnl": Analisis.objects.filter(
            tipo=Analisis.Tipo.PNL
        ).count(),
    }
    return JsonResponse(resumen)
