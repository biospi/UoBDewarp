#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
from pathlib import Path
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import cv2

from dewarp import Defisheye

import json

SETTINGS_FILE = "settings.json"


def save_settings():
    settings = {
        "folder": folder_var.get(),
        "dtype": dtype_var.get(),
        "format": format_var.get(),
        "fov": fov_var.get(),
        "pfov": pfov_var.get(),
        "angle": angle_var.get(),
        "crop_left": crop_left_var.get(),
        "crop_right": crop_right_var.get(),
        "crop_top": crop_top_var.get(),
        "crop_bottom": crop_bottom_var.get(),
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return
    try:
        with open(SETTINGS_FILE, "r") as f:
            settings = json.load(f)

        folder_var.set(settings.get("folder", ""))
        dtype_var.set(settings.get("dtype", "stereographic"))
        format_var.set(settings.get("format", "circular"))
        fov_var.set(settings.get("fov", "180"))
        pfov_var.set(settings.get("pfov", "120"))
        angle_var.set(settings.get("angle", "-0.4"))
        crop_left_var.set(settings.get("crop_left", "0"))
        crop_right_var.set(settings.get("crop_right", "0"))
        crop_top_var.set(settings.get("crop_top", "0"))
        crop_bottom_var.set(settings.get("crop_bottom", "0"))
    except Exception as e:
        print(e)


def process_folder():
    save_settings()
    folder = folder_var.get().strip()
    if not folder or not Path(folder).exists():
        messagebox.showerror("Error", "Please select a valid folder.")
        return

    try:
        fov = float(fov_var.get())
        pfov = float(pfov_var.get())
        angle = float(angle_var.get())
        crop_left = int(crop_left_var.get())
        crop_right = int(crop_right_var.get())
        crop_top = int(crop_top_var.get())
        crop_bottom = int(crop_bottom_var.get())
    except ValueError:
        messagebox.showerror("Error", "One or more parameters are invalid (must be numeric).")
        return

    dtype = dtype_var.get()
    fmt = format_var.get()

    mp4_files = list(Path(folder).glob("*.mp4"))
    if not mp4_files:
        messagebox.showinfo("No Videos", "No .mp4 files found in selected folder.")
        return

    status_label.config(text="Calculating total frames...")

    # -------- Calculate total frames for progress bar --------
    total_frames = 0
    for video in mp4_files:
        cap = cv2.VideoCapture(str(video))
        total_frames += int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

    if total_frames == 0:
        messagebox.showerror("Error", "No readable frames found.")
        return

    progress_bar.config(maximum=total_frames, value=0)
    progress_bar.pack(fill="x", padx=10, pady=(0, 0))
    status_label.config(text=f"Processing...")

    def run():
        processed_frames = 0

        for video_file in mp4_files:
            if "_dewarped" in video_file.name:
                print(f"already dewarped! {video_file}")
                continue
            output_file = video_file.with_name(video_file.stem + "_dewarped.mp4")
            Path(output_file).unlink(missing_ok=True)

            cap = cv2.VideoCapture(str(video_file))
            if not cap.isOpened():
                continue

            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(str(output_file), fourcc, fps, (width, height))

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                obj = Defisheye(
                    frame,
                    dtype=dtype,
                    format=fmt,
                    fov=fov,
                    pfov=pfov,
                    angle=angle,
                    crop_left=crop_left,
                    crop_right=crop_right,
                    crop_top=crop_top,
                    crop_bottom=crop_bottom,
                )

                dewarped_frame = obj.convert()

                if dewarped_frame.shape[:2] != (height, width):
                    dewarped_frame = cv2.resize(dewarped_frame, (width, height))

                writer.write(dewarped_frame)

                processed_frames += 1
                # Update progress safely via GUI thread
                root.after(0, lambda v=processed_frames: progress_bar.config(value=v))

            cap.release()
            writer.release()

        root.after(0, lambda: status_label.config(text="Finished"))
        root.after(0, lambda: messagebox.showinfo("Done", "All videos processed successfully."))

    threading.Thread(target=run, daemon=True).start()


def browse_folder():
    path = filedialog.askdirectory()
    if path:
        folder_var.set(path)


# GUI Setup
root = ttk.Window(themename="flatly")
root.title("Video Dewarping Tool")
root.geometry("600x540")
root.resizable(False, False)

pad = 8

ttk.Label(root, text="Select Folder Containing .mp4 Files", font=("Segoe UI", 11, "bold")).pack(pady=(10,5))

folder_frame = ttk.Frame(root)
folder_frame.pack(fill="x", padx=pad)

folder_var = tk.StringVar()
folder_entry = ttk.Entry(folder_frame, textvariable=folder_var)
folder_entry.pack(side="left", fill="x", expand=True, padx=(0,5))

ttk.Button(folder_frame, text="Browse", bootstyle=PRIMARY, command=browse_folder).pack(side="right")

ttk.Separator(root).pack(fill="x", pady=10)

params_frame = ttk.Frame(root)
params_frame.pack(padx=pad, pady=5, fill="x")

### dtype & format dropdowns
dtype_var = tk.StringVar(value="stereographic")
format_var = tk.StringVar(value="circular")

dtype_row = ttk.Frame(params_frame)
dtype_row.pack(fill="x", pady=4)
ttk.Label(dtype_row, text="Projection Model", width=20).pack(side="left")
ttk.Combobox(dtype_row, textvariable=dtype_var,
             values=["orthographic", "equalarea", "linear", "stereographic"],
             state="readonly", width=16).pack(side="left", padx=(5,10))
ttk.Label(dtype_row, text="Controls mapping style", bootstyle="secondary").pack(side="left")

format_row = ttk.Frame(params_frame)
format_row.pack(fill="x", pady=4)
ttk.Label(format_row, text="Format (Lens Layout)", width=20).pack(side="left")
ttk.Combobox(format_row, textvariable=format_var,
             values=["circular", "fullframe"],
             state="readonly", width=16).pack(side="left", padx=(5,10))
ttk.Label(format_row, text="Circular = typical fisheye", bootstyle="secondary").pack(side="left")

### Numeric controls
fov_var = tk.StringVar(value="180")
pfov_var = tk.StringVar(value="120")
angle_var = tk.StringVar(value="-0.4")
crop_left_var = tk.StringVar(value="0")
crop_right_var = tk.StringVar(value="0")
crop_top_var = tk.StringVar(value="0")
crop_bottom_var = tk.StringVar(value="0")

params = [
    ("Field of View (fov)", fov_var, "Range 90–220. 180 works for most 360 cams."),
    ("Perspective FOV (pfov)", pfov_var, "Wider output view. 120 recommended."),
    ("Rotation Angle", angle_var, "Correct horizon tilt."),
    ("Crop Left", crop_left_var, "Remove warped edge."),
    ("Crop Right", crop_right_var, "Remove warped edge."),
    ("Crop Top", crop_top_var, "Remove warped edge."),
    ("Crop Bottom", crop_bottom_var, "Remove warped edge."),
]


for label, var, hint in params:
    row = ttk.Frame(params_frame)
    row.pack(fill="x", pady=3)
    ttk.Label(row, text=label, width=20).pack(side="left")
    ttk.Entry(row, textvariable=var, width=10).pack(side="left", padx=(5,10))
    ttk.Label(row, text=hint, bootstyle="secondary").pack(side="left")

ttk.Button(root, text="Start Dewarping", bootstyle=SUCCESS, command=process_folder).pack(pady=20)

# NEW: Progress bar (initially hidden until work begins)
progress_bar = ttk.Progressbar(root, bootstyle=INFO)

status_label = ttk.Label(root, text="Ready", anchor="center")
status_label.pack(fill="x", pady=(0,10))

load_settings()

root.mainloop()
