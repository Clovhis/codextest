# System Hardware Inspector - GUI application for Windows
# Requires PyQt5, psutil, wmi, GPUtil
# To compile to a standalone Windows executable with a custom icon using pyinstaller:
#   1. Install PyInstaller: pip install pyinstaller
#   2. Place an icon file named 'icon.ico' in this directory.
#   3. Run:
#        pyinstaller --onefile --windowed --icon=icon.ico system_hardware_inspector.py
#   The executable will be generated in the 'dist' folder.

import sys
import os
import platform
import hashlib
import json
from datetime import date
from pathlib import Path

from cryptography.fernet import Fernet
from fpdf import FPDF
from openai import AzureOpenAI

from PyQt5 import QtWidgets, QtGui, QtCore
import psutil

try:
    import wmi
except ImportError:  # wmi may not be present on non-Windows systems
    wmi = None

try:
    import GPUtil
except ImportError:
    GPUtil = None


def get_cpu_full_name() -> str:
    """Return full CPU name across platforms."""
    if wmi:
        try:
            c = wmi.WMI()
            procs = c.Win32_Processor()
            if procs:
                name = procs[0].Name
                if name:
                    return name.strip()
        except Exception:
            pass

    system = platform.system()
    if system == "Linux":
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    elif system == "Darwin":
        import subprocess

        try:
            output = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True
            )
            return output.strip()
        except Exception:
            pass

    return platform.processor() or platform.uname().processor


def format_bytes(size: int) -> str:
    """Return size in human-readable format."""
    power = 1024
    n = 0
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    while size >= power and n < len(units) - 1:
        size /= power
        n += 1
    return f"{size:.2f} {units[n]}"


def get_cpu_info() -> str:
    uname = platform.uname()
    cpu_model = uname.processor or platform.processor()
    full_name = get_cpu_full_name()
    cores_physical = psutil.cpu_count(logical=False)
    cores_logical = psutil.cpu_count(logical=True)
    freq = psutil.cpu_freq()
    if freq:
        freq_info = f"{freq.current:.2f} MHz"
    else:
        freq_info = "N/A"
    info = [
        f"CPU: {cpu_model}",
        f"Nombre completo: {full_name}",
        f"Cores (Physical): {cores_physical}",
        f"Cores (Logical): {cores_logical}",
        f"Frequency: {freq_info}",
    ]
    return "\n".join(info)


def get_ram_info() -> str:
    """Return detailed RAM information including brand, type, speed and size."""
    if wmi:
        try:
            c = wmi.WMI()
            modules = c.Win32_PhysicalMemory()
            if modules:
                lines = []
                total = 0
                type_map = {
                    20: "DDR",
                    21: "DDR2",
                    24: "DDR3",
                    26: "DDR4",
                    34: "DDR5",
                }
                for m in modules:
                    manufacturer = (m.Manufacturer or "Unknown").strip()
                    mem_type_val = (
                        getattr(m, "SMBIOSMemoryType", None)
                        or getattr(m, "MemoryType", None)
                    )
                    mem_type = type_map.get(int(mem_type_val), "Unknown") if mem_type_val else "Unknown"
                    speed = (
                        f"{int(m.Speed)} MHz" if getattr(m, "Speed", None) else "N/A"
                    )
                    size = int(getattr(m, "Capacity", 0) or 0)
                    total += size
                    lines.append(
                        f"{manufacturer} - {mem_type} - {speed} - {format_bytes(size)}"
                    )
                lines.append(f"RAM Total: {format_bytes(total)}")
                return "\n".join(lines)
        except Exception:
            pass
    mem = psutil.virtual_memory()
    return f"RAM Total: {format_bytes(mem.total)}"


def get_disk_info() -> str:
    """Return information about system disks including a basic type guess."""
    disks = []

    if wmi:
        try:
            c = wmi.WMI()
            for disk in c.Win32_DiskDrive():
                model = disk.Model or disk.Caption
                try:
                    size = format_bytes(int(disk.Size))
                except Exception:
                    size = "N/A"

                interface = (disk.InterfaceType or "").upper()
                model_upper = model.upper()

                if "NVME" in interface or "NVME" in model_upper:
                    disk_type = "NVMe"
                elif "SSD" in model_upper:
                    disk_type = "SSD"
                else:
                    disk_type = "HDD"

                disks.append(f"{model} - {size} - {disk_type}")
        except Exception:
            disks = []

    if not disks:
        partitions = psutil.disk_partitions()
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                size = format_bytes(usage.total)
            except PermissionError:
                size = "N/A"
            disks.append(f"{p.device} ({p.mountpoint}) - {size}")

    return "Disks:\n" + "\n".join(disks)


def get_gpu_info() -> str:
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                lines = [f"GPU: {g.name}" for g in gpus]
                return "\n".join(lines)
        except Exception:
            pass
    if wmi:
        try:
            c = wmi.WMI()
            gpus = c.Win32_VideoController()
            lines = [f"GPU: {g.Name}" for g in gpus if g.Name]
            return "\n".join(lines)
        except Exception:
            pass
    return "GPU information not available"


def get_motherboard_info() -> str:
    if wmi:
        try:
            c = wmi.WMI()
            boards = c.Win32_BaseBoard()
            lines = [f"Motherboard: {b.Manufacturer} {b.Product}" for b in boards]
            return "\n".join(lines)
        except Exception:
            pass
    return "Motherboard information not available"


def get_os_info() -> str:
    """Return the user's operating system."""
    system = platform.system()
    release = platform.release()
    version = platform.version()
    return f"Sistema Operativo: {system} {release} ({version})"


def gather_hardware_info() -> str:
    sections = [
        get_cpu_info(),
        get_ram_info(),
        get_disk_info(),
        get_gpu_info(),
        get_motherboard_info(),
    ]
    info = "\n\n".join(sections)
    info += f"\n\n{get_os_info()}"
    return info


def _load_secure_env(secure_path: Path = Path(".env.secure"), key_path: Path = Path(".key")) -> None:
    """Load encrypted environment variables into os.environ."""
    if not secure_path.exists() or not key_path.exists():
        raise FileNotFoundError("Archivos de credenciales no encontrados")

    with key_path.open("rb") as kf:
        key = kf.read()
    fernet = Fernet(key)
    with secure_path.open("rb") as sf:
        decrypted = fernet.decrypt(sf.read())

    for line in decrypted.decode().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


def _create_ai_client() -> AzureOpenAI:
    """Return configured AzureOpenAI client using loaded env vars."""
    return AzureOpenAI(
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
    )


SYSTEM_PROMPT = (
    "Sos un asistente argentino con buena onda. Dedicado a ayudar a gamers con "
    "presupuestos limitados. Tu tarea es recomendar mejoras al hardware actual "
    "con una excelente relación costo-beneficio, priorizando componentes que se "
    "consigan en Argentina. Evaluá CPU, GPU, RAM y almacenamiento. Indicá marcas, "
    "modelos, gamas y precios estimados en pesos argentinos."
)


def run_ai_analysis(hardware_info: str) -> str:
    """Send hardware info to Azure OpenAI and return its response."""
    _load_secure_env()
    client = _create_ai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": hardware_info},
        ],
    )
    return response.choices[0].message.content.strip()


def export_pdf(hardware_info: str, recommendations: str, output: Path = Path("reporte_gamer_ai.pdf")) -> Path:
    """Generate a PDF report using FPDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, 15)

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Reporte Gamer AI", ln=True, align="C")

    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Fecha: {date.today().isoformat()}", ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Hardware detectado", ln=True)
    pdf.set_font("Helvetica", size=11)
    for line in hardware_info.splitlines():
        pdf.multi_cell(0, 8, line)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Recomendaciones", ln=True)
    pdf.set_font("Helvetica", size=11)
    for line in recommendations.splitlines():
        pdf.multi_cell(0, 8, line)

    pdf.output(str(output))
    return output


def _system_hash() -> str:
    """Create a simple hardware-based hash to track usage."""
    base = f"{platform.node()}_{get_cpu_full_name()}_{platform.system()}"
    return hashlib.sha256(base.encode()).hexdigest()


def can_use_ai_today(log_path: Path = Path("usage_log.json")) -> bool:
    """Return True if the AI button can be used today, updating log."""
    identifier = _system_hash()
    today = date.today().isoformat()
    data = {}
    if log_path.exists():
        try:
            data = json.loads(log_path.read_text())
        except Exception:
            data = {}

    last_use = data.get(identifier)
    if last_use == today:
        return False

    data[identifier] = today
    log_path.write_text(json.dumps(data))
    return True


def generate_gaming_suggestions() -> str:
    """Devuelve sugerencias argentas para potenciar el rendimiento gamer."""
    suggestions = []

    freq = psutil.cpu_freq()
    if freq and freq.current < 3000:
        suggestions.append("Cambiá el micro por uno más picante.")

    mem = psutil.virtual_memory()
    if mem.total < 8 * 1024 ** 3:
        suggestions.append("Meté más RAM que estás cortina para juegos.")

    gpu_detected = False
    if GPUtil:
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu_detected = True
                if gpus[0].memoryTotal < 4:
                    suggestions.append(
                        "Poné una placa con mínimo 4 GB de VRAM y vas a ir de diez."
                    )
        except Exception:
            pass

    if not gpu_detected and wmi:
        try:
            c = wmi.WMI()
            gpus = c.Win32_VideoController()
            gpu_detected = bool(gpus)
        except Exception:
            pass

    if not gpu_detected:
        suggestions.append(
            "Clavale una placa de video dedicada si querés que rinda posta."
        )

    if not suggestions:
        suggestions.append("Tu PC ya está bastante pulenta para jugar.")

    return "\n".join(suggestions)


class AIWorker(QtCore.QThread):
    """Thread to run the AI analysis without freezing the UI."""

    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def run(self) -> None:
        try:
            self.progress.emit(0, "Recolectando información del sistema...")
            hardware = gather_hardware_info()

            self.progress.emit(25, "Cargando modelo de IA...")
            recommendations = run_ai_analysis(hardware)

            self.progress.emit(75, "Exportando reporte en PDF...")
            pdf_path = export_pdf(hardware, recommendations)

            self.progress.emit(100, "Listo")
            self.finished.emit(str(pdf_path))
        except Exception as exc:
            self.error.emit(str(exc))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Hardware Inspector")
        self.resize(600, 400)
        self.setup_ui()
        self.set_dark_theme()
        self.worker = None

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)

        scan_btn = QtWidgets.QPushButton("Escanear hardware")
        save_btn = QtWidgets.QPushButton("Guardar como TXT")
        self.ai_btn = QtWidgets.QPushButton("Analizar con Inteligencia Artificial")
        self.ai_btn.setStyleSheet(
            "background-color: #f39c12; color: white; font-size: 16px;"
        )
        self.ai_btn.setFixedHeight(50)

        scan_btn.clicked.connect(self.scan_hardware)
        save_btn.clicked.connect(self.save_to_txt)
        self.ai_btn.clicked.connect(self.start_ai_analysis)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(scan_btn)
        button_layout.addWidget(save_btn)

        layout = QtWidgets.QVBoxLayout(central)
        layout.addLayout(button_layout)
        layout.addWidget(self.text_edit)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_label = QtWidgets.QLabel()
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.ai_btn, alignment=QtCore.Qt.AlignRight)

    def set_dark_theme(self):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.black)
        palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        self.setPalette(palette)

    def scan_hardware(self):
        info = gather_hardware_info()
        self.text_edit.setPlainText(info)

    def save_to_txt(self):
        text = self.text_edit.toPlainText()
        if not text:
            return
        path = Path("hardware_info.txt")
        with path.open("w", encoding="utf-8") as f:
            f.write(text)
        QtWidgets.QMessageBox.information(self, "Guardado", f"Información guardada en {path.resolve()}")

    def start_ai_analysis(self):
        """Launch AI analysis if daily limit allows it."""
        if not can_use_ai_today():
            QtWidgets.QMessageBox.warning(
                self,
                "Límite alcanzado",
                "Ya utilizaste el análisis con IA hoy. Intentá mañana.",
            )
            return

        self.worker = AIWorker()
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.analysis_finished)
        self.worker.error.connect(self.analysis_error)
        self.ai_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("")
        self.worker.start()

    def update_progress(self, value: int, message: str) -> None:
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def analysis_finished(self, pdf_path: str) -> None:
        self.ai_btn.setEnabled(True)
        QtWidgets.QMessageBox.information(
            self,
            "Reporte generado",
            f"Reporte guardado en {Path(pdf_path).resolve()}",
        )

    def analysis_error(self, message: str) -> None:
        self.ai_btn.setEnabled(True)
        QtWidgets.QMessageBox.critical(self, "Error", message)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
