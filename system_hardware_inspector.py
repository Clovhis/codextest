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
    cores_physical = psutil.cpu_count(logical=False)
    cores_logical = psutil.cpu_count(logical=True)
    freq = psutil.cpu_freq()
    if freq:
        freq_info = f"{freq.current:.2f} MHz"
    else:
        freq_info = "N/A"
    info = [
        f"CPU: {cpu_model}",
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
    return "\n\n".join(sections)


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


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("System Hardware Inspector")
        self.resize(600, 400)
        self.setup_ui()
        self.set_dark_theme()

    def setup_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)

        scan_btn = QtWidgets.QPushButton("Escanear hardware")
        save_btn = QtWidgets.QPushButton("Guardar como TXT")
        suggest_btn = QtWidgets.QPushButton("Sugerencia")
        suggest_btn.setStyleSheet("background-color: #f39c12; color: white;")

        scan_btn.clicked.connect(self.scan_hardware)
        save_btn.clicked.connect(self.save_to_txt)
        suggest_btn.clicked.connect(self.show_suggestions)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(scan_btn)
        button_layout.addWidget(save_btn)

        layout = QtWidgets.QVBoxLayout(central)
        layout.addLayout(button_layout)
        layout.addWidget(self.text_edit)
        layout.addWidget(suggest_btn, alignment=QtCore.Qt.AlignRight)

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
