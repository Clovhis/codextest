# System Hardware Inspector

Este repositorio incluye un script en Python que muestra la información de hardware del sistema en una interfaz gráfica moderna basada en PyQt5.
La aplicación detalla ahora la marca, tipo, velocidad y capacidad de cada módulo de memoria RAM. También presenta el nombre completo del CPU y al final de la lista indica el sistema operativo en uso.

## Requisitos
- Python 3.8+
- PyQt5
- psutil
- wmi (solo Windows)
- GPUtil
- openai
- fpdf2

Instala las dependencias con:
```bash
pip install PyQt5 psutil wmi GPUtil openai fpdf2
```

Antes de ejecutar la opción de análisis con IA, configurá las siguientes
variables de entorno con tus credenciales de Azure OpenAI:

```bash
set AZURE_OPENAI_API_KEY=tu_clave
set AZURE_OPENAI_ENDPOINT=https://tu-endpoint.openai.azure.com/
set AZURE_OPENAI_API_VERSION=2024-02-15-preview
# En Linux o macOS usá `export` en lugar de `set`.
```

## Ejecución
```bash
python system_hardware_inspector.py
```

## Compilar a .exe
Instala PyInstaller y ejecuta:
```bash
pyinstaller --onefile --windowed system_hardware_inspector.py
```
El ejecutable aparecerá en la carpeta `dist`.
