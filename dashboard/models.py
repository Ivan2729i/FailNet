
from django.db import models


class Analisis(models.Model):

    # ==========================================
    # TIPOS DE ANÁLISIS
    # ==========================================

    class Tipo(models.TextChoices):
        SOFI = "sofi", "SOFI"
        DIGITAL_TWIN = "digital_twin", "Digital Twin"
        PNL = "pnl", "PNL"

    # ==========================================
    # ESTADOS
    # ==========================================

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        PROCESANDO = "procesando", "Procesando"
        COMPLETADO = "completado", "Completado"
        ERROR = "error", "Error"

    # ==========================================
    # INFORMACIÓN GENERAL
    # ==========================================

    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices
    )

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    # ==========================================
    # ARCHIVOS CSV
    # ==========================================

    nombre_archivo = models.CharField(
        max_length=255,
        blank=True,
        default=""
    )

    sha256_archivo = models.CharField(
        max_length=64,
        blank=True,
        default=""
    )

    total_registros = models.PositiveIntegerField(
        default=0
    )

    archivo_resultado = models.CharField(
        max_length=500,
        blank=True,
        default=""
    )

    # ==========================================
    # RESULTADOS DEL ANÁLISIS
    # ==========================================

    resultados = models.JSONField(
        default=dict,
        blank=True
    )

    # ==========================================
    # INFORMACIÓN DE PNL
    # ==========================================

    texto_reporte = models.TextField(
        blank=True,
        default=""
    )

    resumen_texto = models.TextField(
        blank=True,
        default=""
    )

    # ==========================================
    # BLOCKCHAIN
    # ==========================================

    indice_blockchain = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    hash_blockchain = models.CharField(
        max_length=64,
        blank=True,
        default=""
    )

    # ==========================================
    # CONTROL DE ERRORES
    # ==========================================

    mensaje_error = models.TextField(
        blank=True,
        default=""
    )

    # ==========================================
    # CONFIGURACIÓN DEL MODELO
    # ==========================================

    class Meta:
        db_table = "analisis"
        ordering = ["-fecha_creacion"]

        verbose_name = "Análisis"
        verbose_name_plural = "Análisis"

    def __str__(self):
        return (
            f"{self.get_tipo_display()} "
            f"- {self.get_estado_display()}"
        )
