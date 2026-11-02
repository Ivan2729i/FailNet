
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
    path('twin/analizar/', views.analizar_archivo_twin, name='api_twin_analizar'),
    path('twin/historial/', views.listar_analisis_twin, name='api_twin_historial'),
    path('twin/analisis/<str:analisis_id>/', views.obtener_analisis_twin, name='api_twin_detalle'),
    path('twin/analisis/<str:analisis_id>/predicciones/', views.paginar_predicciones_twin, name='api_twin_paginar'),
    path('twin/analisis/<str:analisis_id>/descargar/', views.descargar_csv_twin, name='api_twin_descargar'),
]
