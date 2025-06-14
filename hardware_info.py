import argparse
import json
import platform
import subprocess
from pathlib import Path

import psutil
import tkinter as tk
from tkinter import ttk


def get_cpu_info():
    cpu_freq = psutil.cpu_freq()
    freq_info = cpu_freq._asdict() if cpu_freq else {}
    return {
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "frequency": freq_info,
    }


def get_memory_info():
    return psutil.virtual_memory()._asdict()


def get_detailed_disk_info():
    disks = []
    if platform.system() == "Linux":
        try:
            output = subprocess.check_output(
                [
                    "lsblk",
                    "-J",
                    "-o",
                    "NAME,ROTA,TYPE,SIZE,MODEL",
                ]
            ).decode()
            data = json.loads(output)
            for device in data.get("blockdevices", []):
                if device.get("type") == "disk":
                    disks.append(
                        {
                            "name": device.get("name"),
                            "type": (
                                "SSD"
                                if device.get("rota") is False
                                else "HDD"
                            ),
                            "size": device.get("size"),
                            "model": device.get("model"),
                        }
                    )
        except Exception:
            pass
    return disks


def get_disk_info():
    disks = []
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except PermissionError:
            continue
        disks.append({
            "device": part.device,
            "mountpoint": part.mountpoint,
            "fstype": part.fstype,
            "opts": part.opts,
            "usage": usage._asdict(),
        })
    return disks


def get_network_info():
    adapters = {}
    for name, addrs in psutil.net_if_addrs().items():
        adapters[name] = [addr._asdict() for addr in addrs]
    return adapters


def get_motherboard_info():
    board = {}
    if platform.system() == "Linux":
        base_path = Path("/sys/devices/virtual/dmi/id")
        fields = {
            "vendor": base_path / "board_vendor",
            "name": base_path / "board_name",
            "version": base_path / "board_version",
            "serial": base_path / "board_serial",
        }
        for key, path in fields.items():
            try:
                with open(path) as f:
                    board[key] = f.read().strip()
            except Exception:
                continue
    return board


def collect_info():
    return {
        "platform": platform.platform(),
        "processor": platform.processor(),
        "machine": platform.machine(),
        "cpu": get_cpu_info(),
        "memory": get_memory_info(),
        "disks": get_disk_info(),
        "disk_details": get_detailed_disk_info(),
        "motherboard": get_motherboard_info(),
        "network": get_network_info(),
    }


def run_cli():
    print(json.dumps(collect_info(), indent=2))


def run_gui():
    root = tk.Tk()
    root.title("Hardware Info")
    root.geometry("700x600")
    style = ttk.Style(root)
    style.theme_use("clam")

    text = tk.Text(root, wrap="none", font=("Helvetica", 10))
    text.pack(expand=True, fill="both")

    def refresh():
        info = collect_info()
        text.delete("1.0", tk.END)
        text.insert(tk.END, json.dumps(info, indent=2))

    refresh_button = ttk.Button(root, text="Refresh", command=refresh)
    refresh_button.pack(pady=10)
    refresh()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Display hardware information")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="show information in the terminal instead of the GUI",
    )
    args = parser.parse_args()

    if args.cli:
        run_cli()
    else:
        run_gui()


if __name__ == "__main__":
    main()
