# Hardware Info App

Este repositorio contiene una sencilla aplicación en Python que muestra información del hardware instalado en el sistema. Requiere `psutil` para obtener los detalles.

## Uso

Instala las dependencias y ejecuta el script. Por defecto se abrirá una interfaz gráfica:

```bash
pip install psutil
python3 hardware_info.py  # Inicia la GUI

# Opcionalmente puedes ejecutar en modo consola
python3 hardware_info.py --cli
```

El programa imprimirá en formato JSON la plataforma, procesador, información de CPU, memoria, discos y adaptadores de red.
También intentará mostrar detalles de los discos (SSD/HDD y modelo) y del motherboard cuando sea posible.

## Crear ejecutable para Windows

Puedes generar un `.exe` usando `pyinstaller`:

```bash
pip install pyinstaller
pyinstaller --onefile hardware_info.py
```

El ejecutable quedará en la carpeta `dist/` y podrás ejecutarlo como cualquier aplicación de Windows.
