"""Tkinter file dialog used by the data-loading scripts to choose their input CSVs."""
import os


def pick_csv(title, initialdir=None):
    """Show an "open file" dialog for a CSV. Returns the chosen path, or None if cancelled."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()  # no empty main window, just the dialog
    root.attributes("-topmost", True)  # keep the dialog in front of the terminal/editor
    try:
        path = filedialog.askopenfilename(
            parent=root,
            title=title,
            initialdir=initialdir if initialdir and os.path.isdir(initialdir) else os.path.dirname(os.path.abspath(__file__)),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
    finally:
        root.destroy()
    return path or None
