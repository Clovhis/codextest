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
import logging
import base64
from datetime import date
from pathlib import Path

from cryptography.fernet import Fernet
from fpdf import FPDF
from openai import AzureOpenAI

from PyQt5 import QtWidgets, QtGui, QtCore
import psutil
from assets import PURPLE_TENTACLE_BASE64

APP_VERSION = "0.0.6"

LOG_FILE = Path("system_hardware_inspector.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

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


def gather_hardware_info() -> str:
    sections = [
        get_cpu_info(),
        get_ram_info(),
        get_disk_info(),
        get_gpu_info(),
        get_motherboard_info(),
    ]
    info = "\n\n".join(sections)
    return info


def _resource_path(name: str) -> Path:
    """Return absolute path to resource, compatible with PyInstaller."""
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parent
    return base / name


def _load_secure_env(secure_path: Path = Path(".env.secure"), key_path: Path = Path(".key")) -> None:
    """Load encrypted environment variables into os.environ."""
    secure_path = _resource_path(secure_path.name)
    key_path = _resource_path(key_path.name)

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
    "Actu\u00e1 como un asistente t\u00e9cnico especializado en hardware para PC Gamers. "
    "Tu personalidad es canchera, habl\u00e1s en argentino y us\u00e1s un tono informal pero "
    "profesional, como un amigo gamer que sabe much\u00edsimo de componentes. "
    "Tu tarea es revisar la configuraci\u00f3n de hardware del usuario y, para cada "
    "componente (CPU, GPU, RAM, motherboard, almacenamiento, fuente, gabinete, perif\u00e9ricos), "
    "hacer una recomendaci\u00f3n basada en la mejor relaci\u00f3n precio/calidad del mercado actual. "
    "Busc\u00e1 informaci\u00f3n actualizada en internet para hacer comparativas y sugerencias reales. "
    "No repitas specs gen\u00e9ricos ni des recomendaciones vagas. No des precios. "
    "Si el componente del usuario es de \u00faltima generaci\u00f3n o tope de gama "
    "(por ejemplo, una RTX 5070 o un Ryzen 9 9950X), felicit\u00e1lo con onda (\"\u00a1Alta placa te compraste, pap\u00e1!\") y no le hagas recomendaciones para cambiarlo. "
    "Pas\u00e1 directamente al siguiente componente. "
    "Respond\u00e9 siempre de forma clara, en un solo bloque, con una recomendaci\u00f3n concreta por componente. "
    "Ejemplo de tono: \"Che, esa placa de video est\u00e1 buena, pero por el mismo precio pod\u00e9s ir por una 4060 Ti que rinde m\u00e1s en 1080p. Si jug\u00e1s competitivo, te conviene esa. Ah, y no te olvides de una buena fuente que la banque, m\u00ednimo 600W 80 Plus.\" "
    "Nunca uses lenguaje t\u00e9cnico complejo sin explicarlo de forma simple. "
    "Arranc\u00e1 diciendo: \"Dale, vamos a ver qu\u00e9 ten\u00e9s en esa nave gamer...\""
)



def run_ai_analysis(hardware_info: str) -> str:
    """Send hardware info to Azure OpenAI and return its response."""
    _load_secure_env()
    client = _create_ai_client()
    model_name = "gpt-4o-mini"
    logging.info("Usando modelo de IA %s", model_name)
    logging.info("Enviando informaci\u00f3n a OpenAI")
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": hardware_info},
        ],
    )
    logging.info("Respuesta recibida de la IA")
    return response.choices[0].message.content.strip()


def export_pdf(hardware_info: str, recommendations: str, output: Path = Path("reporte_gamer_ai.pdf")) -> Path:
    """Generate a PDF report using FPDF."""
    def _sanitize(text: str) -> str:
        """Remove characters unsupported by FPDF's latin-1 encoding."""
        return text.encode("latin-1", errors="replace").decode("latin-1")

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
    for line in _sanitize(hardware_info).splitlines():
        pdf.multi_cell(0, 8, line)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Recomendaciones", ln=True)
    pdf.set_font("Helvetica", size=11)
    for line in _sanitize(recommendations).splitlines():
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



class AIWorker(QtCore.QThread):
    """Thread to run the AI analysis without freezing the UI."""

    progress = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal(str, str)  # recommendations, pdf path
    error = QtCore.pyqtSignal(str)

    def run(self) -> None:
        try:
            logging.info("Iniciando recolecci\u00f3n de hardware")
            self.progress.emit(0, "Recolectando informaci\u00f3n del sistema...")
            hardware = gather_hardware_info()

            logging.info("Conectando con OpenAI")
            self.progress.emit(20, "Conectando con los servicios de OpenAI...")

            self.progress.emit(40, "Esperando respuesta de OpenAI...")
            recommendations = run_ai_analysis(hardware)

            self.progress.emit(60, "Evaluando hardware...")
            logging.info("Generando PDF")
            self.progress.emit(80, "Generando reporte en PDF...")
            pdf_path = export_pdf(hardware, recommendations)

            logging.info("Proceso completado")
            self.progress.emit(100, "Listo")
            self.finished.emit(recommendations, str(pdf_path))
        except Exception as exc:
            logging.exception("Error en el hilo de IA")
            self.error.emit(str(exc))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"System Hardware Inspector v{APP_VERSION}")
        self.resize(800, 600)
        self.setup_ui()
        self.set_dark_theme()
        self.worker = None
        self.scan_hardware()

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.logo_label = QtWidgets.QLabel()
        logo_pix = QtGui.QPixmap()
        logo_pix.loadFromData(base64.b64decode(PURPLE_TENTACLE_BASE64))
        if not logo_pix.isNull():
            logo_pix = logo_pix.scaledToHeight(150, QtCore.Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pix)
            self.logo_label.setAlignment(QtCore.Qt.AlignCenter)

        self.hardware_edit = QtWidgets.QTextEdit()
        self.hardware_edit.setReadOnly(True)
        self.hardware_edit.setStyleSheet("font-size: 14px;")

        self.reco_edit = QtWidgets.QTextEdit()
        self.reco_edit.setReadOnly(True)
        self.reco_edit.setStyleSheet("font-size: 14px;")

        save_btn = QtWidgets.QPushButton("Guardar como TXT")
        self.ai_btn = QtWidgets.QPushButton("Analizar con Inteligencia Artificial")
        btn_style = (
            "QPushButton {"
            "background-color: #70267a;"
            "color: white;"
            "font-size: 14px;"
            "padding: 8px;"
            "border-radius: 4px;"
            "}"
            "QPushButton:hover {"
            "background-color: #a041cc;"
            "}"
        )
        save_btn.setStyleSheet(btn_style)
        self.ai_btn.setStyleSheet(btn_style)
        self.ai_btn.setFixedHeight(50)

        save_btn.clicked.connect(self.save_to_txt)
        self.ai_btn.clicked.connect(self.start_ai_analysis)

        save_btn.clicked.connect(lambda: self.animate_button(save_btn))
        self.ai_btn.clicked.connect(lambda: self.animate_button(self.ai_btn))

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(save_btn)

        text_layout = QtWidgets.QHBoxLayout()
        text_layout.addWidget(self.hardware_edit)
        text_layout.addWidget(self.reco_edit)

        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(self.logo_label)
        layout.addLayout(button_layout)
        layout.addLayout(text_layout)
        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            "QProgressBar::chunk { background-color: #39FF14; }"
        )
        self.progress_label = QtWidgets.QLabel()
        self.progress_label.setStyleSheet("font-size: 12px; color: white;")
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.ai_btn, alignment=QtCore.Qt.AlignRight)
        footer = QtWidgets.QLabel("By Clovhis")
        footer.setAlignment(QtCore.Qt.AlignCenter)
        footer.setStyleSheet("color: #39FF14;")
        layout.addWidget(footer)

    def set_dark_theme(self):
        palette = QtGui.QPalette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor("#301934"))
        palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor("#3d1e4d"))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor("#502565"))
        palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor("#502565"))
        palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor("#39FF14"))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor("#39FF14"))
        palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        self.setPalette(palette)

    def scan_hardware(self):
        info = gather_hardware_info()
        self.hardware_edit.setPlainText(info)

    def save_to_txt(self):
        text = self.hardware_edit.toPlainText()
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

    def analysis_finished(self, recommendations: str, pdf_path: str) -> None:
        self.ai_btn.setEnabled(True)
        self.reco_edit.setPlainText(recommendations)
        QtWidgets.QApplication.beep()
        QtWidgets.QMessageBox.information(
            self,
            "Reporte generado",
            f"Reporte guardado en {Path(pdf_path).resolve()}",
        )

    def analysis_error(self, message: str) -> None:
        self.ai_btn.setEnabled(True)
        QtWidgets.QApplication.beep()
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def animate_button(self, button: QtWidgets.QPushButton) -> None:
        rect = button.geometry()
        bigger = rect.adjusted(-5, -5, 5, 5)
        animation = QtCore.QPropertyAnimation(button, b"geometry")
        animation.setDuration(200)
        animation.setStartValue(rect)
        animation.setKeyValueAt(0.5, bigger)
        animation.setEndValue(rect)
        animation.start(QtCore.QAbstractAnimation.DeleteWhenStopped)
        button._animation = animation


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(QtGui.QFont("Arial", 12))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
