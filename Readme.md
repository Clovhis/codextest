# System Hardware Inspector

Este repositorio incluye un script en Python que muestra la información de hardware del sistema en una interfaz gráfica moderna basada en PyQt5.

## Requisitos
- Python 3.8+
- PyQt5
- psutil
- wmi (solo Windows)
- GPUtil

Instala las dependencias con:
```bash
pip install PyQt5 psutil wmi GPUtil
```

## Ejecución
```bash
python system_hardware_inspector.py
```

## Compilar a .exe
Instala PyInstaller y ejecuta:
```bash
pyinstaller --onefile --windowed --icon=icon.ico system_hardware_inspector.py
```
El ejecutable aparecerá en la carpeta `dist`.
