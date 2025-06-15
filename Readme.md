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
pip install PyQt5 psutil wmi GPUtil openai fpdf2 cryptography
```

Antes de ejecutar la aplicación debes generar un archivo cifrado con las
credenciales de Azure OpenAI. Ejecuta una sola vez el script
`generate_credentials.py` y completa los datos solicitados. Esto creará los
archivos `azure_credentials.enc` y `credentials.key` que **no** deberían
compartirse ni subirse al repositorio.

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
