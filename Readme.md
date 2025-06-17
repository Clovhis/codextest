# System Hardware Inspector

Este repositorio incluye un script en Python que muestra la información de hardware del sistema en una interfaz gráfica moderna basada en PyQt5.
La aplicación detalla ahora la marca, tipo, velocidad y capacidad de cada módulo de memoria RAM y el nombre completo del CPU.
La imagen del tentáculo púrpura está embebida en el código, evitando archivos binarios adicionales.
Al iniciarse, la herramienta escanea el hardware de forma automática y lo exhibe en la ventana izquierda. A la derecha aparecerán las recomendaciones de la IA una vez que finalice el análisis, y esas sugerencias también se guardan en un PDF.

## Requisitos
- Python 3.8+
- PyQt5
- psutil
- wmi (solo Windows)
- GPUtil
- cryptography
- fpdf
- openai

Instala las dependencias con:
```bash
pip install PyQt5 psutil wmi GPUtil cryptography fpdf openai
```

### Configuración de credenciales
1. Creá un archivo `.env` con las variables `AZURE_OPENAI_API_KEY`,
   `AZURE_OPENAI_ENDPOINT` y `AZURE_OPENAI_API_VERSION`.
2. Ejecutá `python setup_keys.py` para generar `.env.secure` y `.key`.
   Ambos archivos están listados en `.gitignore` para mantener tus claves fuera
   del repositorio.

## Ejecución
```bash
python system_hardware_inspector.py
```

La aplicación registra toda la actividad en el archivo
`system_hardware_inspector.log`, útil para depurar errores de conexión
o fallos inesperados.

## Descargar la aplicación
No es necesario compilar manualmente. Cada versión estable se publica
como ejecutable en la sección **Releases** de GitHub. Solo descargá la
última versión para tu sistema operativo y ejecutala.
