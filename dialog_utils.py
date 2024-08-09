# -*- coding: utf-8 -*-
"""
Module with utilities for managing the GUI
"""

import os
import tkinter as tk
import tkinter.font as tkFont
from tkinter import Variable, ttk
from tkinter import scrolledtext as ScrolledText


def prepare_fonts(root, verbose=False):
    """Setup the available fonts to be used with the most appropriate size."""
    defaultfont = tkFont.Font(font="TkDefaultFont")
    fixedfont = tkFont.Font(font="TkFixedFont")
    default_size = defaultfont.cget("size")
    screen_width, _screen_height = root.winfo_screenwidth(), root.winfo_screenheight()
    if verbose:
        print(f"TkDefaultFont={defaultfont.actual()}")
        print(f"TkFixedtFont={fixedfont.actual()}")
        print(f"screen_width={screen_width}")
    if 1024 < screen_width <= 1440:
        default_size = 10
    elif 1440 < screen_width <= 1920:
        default_size = 12
    elif 1920 < screen_width:
        default_size = 14
    if verbose:
        print(f"default_size={default_size}")

    families = tkFont.families()
    if verbose:
        print(f"Available font families={sorted(families)}")
    if "DejaVu Sans" in families:
        family_variable = "DejaVu Sans"
        family_mono = "DejaVu Sans Mono"
    elif "Noto Sans" in families:
        family_variable = "Noto Sans"
        family_mono = "Noto Mono"
    else:
        if "Times New Roman" in families:
            family_variable = "Times New Roman"
        else:
            family_variable = defaultfont.cget("family")
        if "Courier" in families:
            family_mono = "Courier"
        else:
            family_mono = fixedfont.cget("family")
    if verbose:
        print(
            f"Family variable={family_variable}, mono={family_mono}, size={default_size}"
        )
    return {"variable": family_variable, "mono": family_mono, "size": default_size}


def resource_path(relative_path: str):
    """To handle external resources within exe package"""
    bundle_dir = os.path.abspath(os.path.dirname(__file__))
    path_to_data = os.path.join(bundle_dir, relative_path)
    return path_to_data


def create_icon_button(
    parent, image: str, col: int, row: int, size: int = 32, action=""
) -> tuple[tk.Button, tk.PhotoImage]:
    """
    Create a button with only a icon image
    """
    img = tk.PhotoImage(file=resource_path(image))
    # With image width and height are in screen units, aka "pixels"
    btn = tk.Button(
        parent,
        image=img,
        height=size,
        width=size,
        borderwidth=0,
        highlightthickness=0,
        bd=0,
        command=action,
    )
    btn.grid(column=col, row=row, sticky="e")
    return (btn, img)


def create_button(
    parent, text: str, image: str, col: int, row: int, action=""
) -> tuple[tk.Button, tk.PhotoImage]:
    """
    Create a button with an optional image

    Images taken from https://commons.wikimedia.org/wiki/Category:Gartoon_icons
    """
    img = None
    if image:
        img = tk.PhotoImage(file=resource_path(image))
        # With image width and height are in screen units, aka "pixels"
        btn = tk.Button(
            parent,
            text="  " + text,
            image=img,
            compound=tk.LEFT,
            height=32,
            width=32,
            # underline=2,
            command=action,
        )
    else:
        # Without image, width and height are in lines of text
        btn = tk.Button(
            parent,
            text=text,
            height=2,
            width=4,
            # underline=0,
            command=action,
        )
    btn.grid(column=col, row=row, sticky="nsew")
    return (btn, img)


def create_combo(
    parent, text: str, textvariable: Variable, options: list[str], col: int, row: int
) -> ttk.Combobox:
    """Create a combo box with a label"""
    tk.Label(parent, text=text).grid(column=col, row=row, sticky="w")
    combo = ttk.Combobox(
        parent, textvariable=textvariable, values=options, width=35, state="readonly"
    )
    combo.grid(column=col + 1, row=row, columnspan=2, sticky="w")
    return combo


def create_entry(parent, text: str, col: int, row: int) -> tk.Entry:
    """Create a entry field with a label"""
    tk.Label(parent, text=text).grid(column=col, row=row, sticky="w")
    entry = tk.Entry(parent, width=35, state="readonly")
    entry.grid(column=col + 1, row=row, columnspan=2, sticky="w")
    return entry


def create_entry_for_dir(
    parent, text: str, col: int, row: int, action=""
) -> tuple[tk.Entry, tk.Button]:
    """Create a entry field with a label and a button to select a dir"""
    tk.Label(parent, text=text).grid(column=col, row=row, sticky="w")
    entry = tk.Entry(parent, width=35, state="normal")
    entry.grid(column=col + 1, row=row, columnspan=2, sticky="w")
    btn = tk.Button(
        parent,
        text="...",
        height=1,
        width=4,
        command=action,
    )
    btn.grid(column=col + 2, row=row, sticky="e")
    return (entry, btn)


def show_textdialog(
    root,
    title: str,
    asset_file: str,
    font_families=None,
    action=None,
) -> tk.Toplevel:
    """Display a new text dialog"""
    if font_families is None:
        font_families = {"variable": "DejaVu Sans", "size": 10}
    with open(resource_path(asset_file), "r", encoding="utf-8") as text:
        lines = text.readlines()

    pop = tk.Toplevel(root)
    pop.title("À propos…")
    pop.geometry("600x600")
    # Center the dialog
    pop.wait_visibility()
    x = root.winfo_x() + (root.winfo_width() - pop.winfo_width()) // 2
    y = root.winfo_y() + (root.winfo_height() - pop.winfo_height()) // 2
    pop.geometry(f"+{x}+{y}")

    # pop.config(bg="white")
    # Add a label to show the title
    label = tk.Label(
        pop,
        text=title,
        justify="center",
        font=(
            font_families["variable"],
            font_families["size"] + 2,
            "bold",
        ),  # "MyFontBigBold",  # ("DejaVu Sans", 12, "bold"),
    )
    label.pack(side=tk.TOP, padx=5, pady=5)
    # Add ScrolledText to allow for styling
    textarea = ScrolledText.ScrolledText(pop, wrap="word", borderwidth=3, height=32)
    textarea.delete(1.0, tk.END)
    for line in lines:
        parse_to_text(line, textarea)
    textarea.tag_config(
        "normal", font=(font_families["variable"], font_families["size"])
    )
    textarea.tag_config(
        "italic", font=(font_families["variable"], font_families["size"], "italic")
    )
    textarea.tag_config(
        "bold", font=(font_families["variable"], font_families["size"], "bold")
    )
    textarea.tag_config(
        "link",
        foreground="blue",
        font=(font_families["variable"], font_families["size"]),
    )
    textarea.pack(side=tk.TOP, padx=5, pady=5)
    textarea.config(state=tk.DISABLED)
    # Add Button to close the modal
    if action is None:
        action = pop.destroy
    button = tk.Button(
        pop,
        text="OK",
        font=(font_families["variable"], font_families["size"]),
        command=action,
    )
    button.pack(side=tk.TOP, padx=5, pady=5)
    return pop


def parse_to_text(line, textarea):
    """
    Insert line into textarea with formating:
    - links between []
    - italic between __
    - bold between **
    """
    buf = ""
    is_italic = False
    is_bold = False
    for car in line:
        if car == "[":
            if len(buf) > 0:
                textarea.insert(tk.END, buf, "normal")
                buf = ""
        elif car == "]":
            textarea.insert(tk.END, buf, "link")
            buf = ""
        elif car == "_":
            if is_italic:
                if len(buf) > 0:
                    textarea.insert(tk.END, buf, "italic")
                buf = ""
                is_italic = False
            else:
                if len(buf) > 0:
                    textarea.insert(tk.END, buf, "normal")
                buf = ""
                is_italic = True
        elif car == "*":
            if is_bold:
                if len(buf) > 0:
                    textarea.insert(tk.END, buf, "bold")
                buf = ""
                is_bold = False
            else:
                if len(buf) > 0:
                    textarea.insert(tk.END, buf, "normal")
                buf = ""
                is_bold = True
        else:
            buf += car
    if len(buf) > 0:
        textarea.insert(tk.END, buf, "normal")
