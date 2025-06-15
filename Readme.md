# System Hardware Inspector

Este repositorio incluye un script en Python que muestra la información de hardware del sistema en una interfaz gráfica moderna basada en PyQt5.
La aplicación detalla ahora la marca, tipo, velocidad y capacidad de cada módulo de memoria RAM. También presenta el nombre completo del CPU y al final de la lista indica el sistema operativo en uso.

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

## Compilar a .exe
Instala PyInstaller y ejecuta:
```bash
pyinstaller --onefile --windowed system_hardware_inspector.py
```
El ejecutable aparecerá en la carpeta `dist`.

Para que el binario pueda cargar las credenciales, copiá los archivos
`.env.secure` y `.key` junto al `.exe` o agregalos al momento de compilar:

```bash
pyinstaller --onefile --windowed \
    --add-data ".env.secure;." --add-data ".key;." \
    system_hardware_inspector.py
```
También podés usar el mismo comando en una sola línea en PowerShell:

```powershell
pyinstaller --onefile --windowed --add-data ".env.secure;." --add-data ".key;." system_hardware_inspector.py
```
