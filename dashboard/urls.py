
from django.urls import path
from . import views

urlpatterns = [
    path("resumen/", views.obtener_resumen, name="api_resumen"),
    path("csrf/", views.obtener_csrf, name="api_csrf"),
    path("sofi/analizar/", views.analizar_archivos_sofi, name="api_sofi_analizar"),
    path("sofi/historial/", views.listar_analisis_sofi, name="api_sofi_historial"),
    path("sofi/analisis/<str:analisis_id>/", views.obtener_analisis_sofi, name="api_sofi_detalle"),
    path("sofi/analisis/<str:analisis_id>/predicciones/", views.paginar_predicciones_sofi, name="api_sofi_paginar"),
    path("sofi/analisis/<str:analisis_id>/descargar/", views.descargar_csv_sofi, name="api_sofi_descargar"),
]
