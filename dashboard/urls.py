
from django.urls import path
from . import views



urlpatterns = [
    path(
        "resumen/",
        views.obtener_resumen,
        name="api_resumen",
    ),
]
