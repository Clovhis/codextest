# System Hardware Inspector - GUI application for Windows
# Requires PyQt5, psutil, wmi, GPUtil
# To compile to a standalone Windows executable with a custom icon using pyinstaller:
#   1. Install PyInstaller: pip install pyinstaller
#   2. Place an icon file named 'icon.ico' in this directory.
#   3. Run:
#        pyinstaller --onefile --windowed --icon=icon.ico system_hardware_inspector.py
#   The executable will be generated in the 'dist' folder.

import sys
import platform
from pathlib import Path
import json
import hashlib
from datetime import datetime, date
import subprocess
import os

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


USAGE_LOG = Path("usage_log.json")

SYSTEM_PROMPT = (
    "Sos un asistente argentino con buena onda. Dedicado a ayudar a gamers con presupuestos limitados. Tu tarea es recomendar mejoras al hardware actual con una excelente relación costo-beneficio, priorizando componentes que se consigan en Argentina. Evaluá CPU, GPU, RAM y almacenamiento. Indicá marcas, modelos, gamas y precios estimados en pesos argentinos."
)


def create_openai_client() -> AzureOpenAI:
    """Return an AzureOpenAI client configured via environment variables."""
    key = os.getenv("AZURE_OPENAI_API_KEY")
    version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    if not key or not endpoint:
        raise ValueError(
            "Azure OpenAI credentials not configured. Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT."
        )
    return AzureOpenAI(api_key=key, api_version=version, azure_endpoint=endpoint)


def compute_hardware_hash() -> str:
    """Return a stable hash representing this machine."""
    base = "|".join(
        [get_cpu_full_name(), get_ram_info(), get_gpu_info(), get_motherboard_info()]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def load_usage_log() -> dict:
    if USAGE_LOG.exists():
        try:
            with USAGE_LOG.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_usage_log(data: dict) -> None:
    with USAGE_LOG.open("w", encoding="utf-8") as f:
        json.dump(data, f)


def create_pdf(hardware_info: str, recommendations: str, path: Path) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Informe de Análisis Gamer con Inteligencia Artificial", ln=1, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Fecha del análisis: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Información de hardware", ln=1)
    pdf.set_font("Arial", "", 12)
    for line in hardware_info.splitlines():
        pdf.multi_cell(0, 8, line)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Recomendaciones", ln=1)
    pdf.set_font("Arial", "", 12)
    for line in recommendations.splitlines():
        pdf.multi_cell(0, 8, line)
    pdf.output(str(path))


def open_pdf_file(path: Path) -> bool:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform.startswith("darwin"):
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
        return True
    except Exception:
        return False


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


class AIAnalysisThread(QtCore.QThread):
    progress = QtCore.pyqtSignal(str, int)
    finished_signal = QtCore.pyqtSignal(str)
    error = QtCore.pyqtSignal(str)

    def __init__(self, hardware_hash: str, parent: QtCore.QObject | None = None):
        super().__init__(parent)
        self.hardware_hash = hardware_hash

    def run(self) -> None:
        try:
            self.progress.emit("Recolectando información del sistema...", 0)
            hw_info = gather_hardware_info()

            self.progress.emit("Conectando con el modelo de IA...", 1)
            client = create_openai_client()
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": hw_info},
            ]

            self.progress.emit("Analizando datos...", 2)
            resp = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
            recommendation = resp.choices[0].message.content.strip()

            self.progress.emit("Generando recomendaciones personalizadas...", 3)
            path = Path("reporte_gamer_ai.pdf")
            create_pdf(hw_info, recommendation, path)

            self.progress.emit("Creando informe en PDF...", 4)
            self.finished_signal.emit(str(path))
        except Exception as e:  # pragma: no cover - network/IO errors
            self.error.emit(str(e))


class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Analizando con IA...")
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel("Iniciando...")
        self.bar = QtWidgets.QProgressBar()
        self.bar.setRange(0, 5)
        layout.addWidget(self.label)
        layout.addWidget(self.bar)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Hardware Inspector")
        self.resize(600, 400)
        self.setup_ui()
        self.set_dark_theme()
        self.check_ai_usage()

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)

        scan_btn = QtWidgets.QPushButton("Escanear hardware")
        save_btn = QtWidgets.QPushButton("Guardar como TXT")
        self.ai_btn = QtWidgets.QPushButton("Analizar con Inteligencia Artificial")
        self.ai_btn.setStyleSheet(
            "background-color: #f39c12; color: white; font-weight: bold; font-size: 16px; padding: 10px;"
        )
        self.ai_btn.setFixedHeight(40)

        scan_btn.clicked.connect(self.scan_hardware)
        save_btn.clicked.connect(self.save_to_txt)
        self.ai_btn.clicked.connect(self.start_ai_analysis)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(scan_btn)
        button_layout.addWidget(save_btn)

        layout = QtWidgets.QVBoxLayout(central)
        layout.addLayout(button_layout)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.ai_btn, alignment=QtCore.Qt.AlignRight)

    def check_ai_usage(self) -> bool:
        self.hardware_hash = compute_hardware_hash()
        log = load_usage_log()
        today = date.today().isoformat()
        if log.get(self.hardware_hash) == today:
            self.ai_btn.setEnabled(False)
            return False
        self.ai_btn.setEnabled(True)
        return True

    def start_ai_analysis(self) -> None:
        if not self.check_ai_usage():
            QtWidgets.QMessageBox.information(
                self, "Aviso", "El análisis con IA ya se realizó hoy." 
            )
            return

        self.progress_dialog = ProgressDialog(self)
        self.progress_dialog.show()

        self.thread = AIAnalysisThread(self.hardware_hash)
        self.thread.progress.connect(self.update_progress)
        self.thread.finished_signal.connect(self.ai_finished)
        self.thread.error.connect(self.ai_error)
        self.thread.start()

    def update_progress(self, message: str, step: int) -> None:
        self.progress_dialog.label.setText(message)
        self.progress_dialog.bar.setValue(step + 1)

    def ai_finished(self, pdf_path: str) -> None:
        self.progress_dialog.close()
        log = load_usage_log()
        log[self.hardware_hash] = date.today().isoformat()
        save_usage_log(log)

        if not open_pdf_file(Path(pdf_path)):
            QtWidgets.QMessageBox.information(
                self,
                "Informe generado",
                f"Reporte guardado en {Path(pdf_path).resolve()}",
            )
        self.check_ai_usage()

    def ai_error(self, message: str) -> None:
        self.progress_dialog.close()
        QtWidgets.QMessageBox.critical(self, "Error", message)

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

    def show_suggestions(self):
        suggestions = generate_gaming_suggestions()
        QtWidgets.QMessageBox.information(self, "Sugerencias", suggestions)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
