#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module for handling the GUI of donating emails with IMAP
"""

import argparse
import datetime
import logging
import os
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import messagebox as tkMessageBox
from tkinter import filedialog as tkFileDialog
from tkinter import ttk

from dialog_utils import (
    create_button,
    create_icon_button,
    create_combo,
    create_entry,
    create_entry_for_dir,
    show_textdialog,
    resource_path,
    prepare_fonts,
)
import imap_server
from imap_account import ImapAccount
from imap_download import ImapDownload
from mbox_delivery import MboxDelivery
from user_pref import UserPreferences

__version__ = "1.2.9"
__appname__ = "donatemail"

logger = logging.getLogger(__appname__)


class DonateGui(tk.Frame):
    """This class defines the graphical user interface + associated functions
    for associated actions
    """

    def __init__(self, parent, *args, **kwargs):
        """Initiate class"""
        self._verbose = kwargs.get("verbose", False)
        if "verbose" in kwargs:
            # Verbose is not known by tk
            del kwargs["verbose"]
        tk.Frame.__init__(self, parent, *args, **kwargs)
        self.root = parent
        self.password_hidden = True
        self.pop_about = None
        self.pop_info_passwd = None
        self.icon = None
        self.font_families = {}
        # Variables to cope with background work
        self.progress_var = tk.IntVar()
        self.working_thread = None
        self.working_operation = None

        self.prefs = UserPreferences(__appname__)
        self.work_dir = self.prefs.get("WorkDir")
        if self.work_dir is None:
            self.work_dir = tempfile.gettempdir()
            self.prefs.set("WorkDir", self.work_dir)
        self.delivery_dir = self.prefs.get("DeliveryDir")
        if self.delivery_dir is None:
            self.delivery_dir = "tmp"
            self.prefs.set("DeliveryDir", self.delivery_dir)
        # Other variables to init...
        self.known_servers = imap_server.ImapServers()
        self.known_servers.read_from_json(resource_path("./assets/servers.json"))
        self.servers = self.known_servers.get_servers()
        # Variables to follow the GUI
        self.selected_server = None
        self.server = None
        self.account = None
        self.folders = []
        self.selected_folder = None

        self.build_gui()

    @property
    def verbose(self) -> bool:
        """Getter for verbose"""
        return self._verbose

    @verbose.setter
    def verbose(self, value: bool):
        """Setter for verbose"""
        self._verbose = value

    def disable_gui_on_work(self):
        """Disable all the GUI during work"""
        self.folders_btn.config(state="disabled")
        self.retrieve_btn.config(state="disabled")
        self.delivery_btn.config(state="disabled")

        self.server_combo.config(state="disabled")
        self.login_entry.config(state="readonly")
        self.password_entry.config(state="readonly")
        self.folders_listbox.config(state="disabled")
        self.foldercounts_checkbox.config(state="disabled")
        self.work_dir_btn.config(state="disabled")
        self.delivery_dir_btn.config(state="disabled")

    def enable_gui_after_work(self, enables_btns: list[tk.Button] = None):
        """Re-enable the GUI after work"""
        if enables_btns is not None:
            for btn in enables_btns:
                btn.config(state="normal")

        self.server_combo.config(state="normal")
        self.login_entry.config(state="normal")
        self.password_entry.config(state="normal")
        self.folders_listbox.config(state="normal")
        self.foldercounts_checkbox.config(state="normal")
        self.work_dir_btn.config(state="normal")
        self.delivery_dir_btn.config(state="normal")

    def on_server_changed(self, _event=None):
        """Handle new server selected"""
        self.server = self.known_servers.get_server(self.selected_server.get())
        if self._verbose:
            print(f"Select server {self.selected_server.get()} for {self.server}")
        self.folders = []
        self.refresh_folders_list()
        self.enable_gui_after_work([self.folders_btn])

    def on_folders(self, _event=None):
        """Generate the list of folders"""
        if self.server is None:
            msg = "Choisissez d'abord un serveur."
            tkMessageBox.showerror("Erreur", msg)
            return
        user = self.login_entry.get().strip()
        password = self.password_entry.get().strip()
        if user is not None and len(user) != 0:
            self.account = ImapAccount(user, password)
        else:
            msg = "Merci de fournir un login avec son mot de passe applicatif."
            tkMessageBox.showerror("Erreur", msg)
            return
        self.disable_gui_on_work()

        self.working_operation = ImapDownload(self.server)
        self.working_operation.verbose = self._verbose
        self.working_operation.account = self.account
        self.root.config(cursor="watch")
        self.working_thread = threading.Thread(
            target=self.working_operation.list_folders,
            args=(self.foldercounts_check_value.get(), self.progress_folder),
            daemon=True,
        )
        self.working_thread.start()

    def progress_folder(
        self, status: str, number: int, total: int, msg: str = ""
    ) -> None:
        """Manage the progress of the loading folder thread"""
        if status == "start":
            self.progress_raz()
        elif status == "running":
            self.progress(status, number, total, msg)
        elif status == "error":
            self.enable_gui_after_work([self.folders_btn])
            self.working_operation.logout()
            self.working_operation = None
            self.root.config(cursor="")
            if len(msg) == 0:
                msg = "Erreur lors de la récupération des dossiers."
            tkMessageBox.showerror("Erreur", msg)
        elif status == "complete":
            self.enable_gui_after_work([self.folders_btn, self.retrieve_btn])
            self.folders = sorted(self.working_operation.folders)
            self.working_operation.logout()
            self.working_operation = None
            self.root.config(cursor="")
            folders_count = len(self.folders)
            self.refresh_folders_list()
            self.progress_raz()
            msg = (
                f"{folders_count} dossiers ont été trouvés.\n"
                "Sélectionnez-en un puis récupérez les courriels."
            )
            tkMessageBox.showinfo("Succès", msg)

    def on_retrieve(self, _event=None):
        """retrieve the mails of the selected folder"""
        if self.selected_folder is None:
            msg = "Choisissez le dossier à récupérer."
            tkMessageBox.showerror("Erreur", msg)
            return
        self.disable_gui_on_work()

        self.working_operation = ImapDownload(self.server)
        self.working_operation.verbose = self._verbose
        self.working_operation.account = self.account
        self.root.config(cursor="watch")
        # Use modified UTF-7 to avoid interoperability issues in filenames
        name_mbox = f"{self.selected_folder.name_in_mutf7}.mbox"
        temp_mbox = os.path.join(self.work_dir, name_mbox)
        try:
            os.remove(temp_mbox)
        except OSError:
            pass
        folder = self.selected_folder

        self.working_thread = threading.Thread(
            target=self.working_operation.get_mails_mbox,
            args=(temp_mbox, folder, self.progress_retrieve),
            daemon=True,
        )
        self.working_thread.start()

    def progress_retrieve(
        self, status: str, number: int, total: int, msg: str = ""
    ) -> None:
        """Manage the progress of the retrieving thread"""
        if status == "start":
            self.progress_raz()
        elif status == "running":
            self.progress(status, number, total, msg)
        elif status == "error":
            self.enable_gui_after_work([self.folders_btn, self.retrieve_btn])
            self.working_operation.logout()
            self.working_operation = None
            self.root.config(cursor="")
            if len(msg) == 0:
                msg = "Erreur lors de la récupération des courriels."
            tkMessageBox.showerror("Erreur", msg)
        elif status == "complete":
            mails_count = number
            self.working_operation.logout()
            self.working_operation = None
            self.root.config(cursor="")
            self.progress_raz()

            if mails_count <= 0:
                self.enable_gui_after_work([self.folders_btn, self.retrieve_btn])
                if len(msg) == 0:
                    msg = "Aucun courriel récupéré !!!"
                tkMessageBox.showerror("Erreur", msg)
            else:
                self.enable_gui_after_work(
                    [self.folders_btn, self.retrieve_btn, self.delivery_btn]
                )
                msg = f"{mails_count} courriels ont été récupérés.\nVous pouvez créer la livraison."
                tkMessageBox.showinfo("Succès", msg)

    def on_delivery(self, _event=None):
        """Prepare the delivery by making a ZIP with the mbox and metadata information"""
        if self.selected_folder is None:
            msg = "Choisissez le dossier à livrer."
            tkMessageBox.showerror("Erreur", msg)
            return
        name_mbox = f"{self.selected_folder.name_in_mutf7}.mbox"
        temp_mbox = os.path.join(self.work_dir, name_mbox)
        if not os.path.exists(temp_mbox):
            msg = f"Le dossier {self.selected_folder.name} n'a pas encore été récupéré !!!"
            tkMessageBox.showerror("Erreur", msg)
            return

        self.root.config(cursor="watch")
        suffix = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        try:
            os.makedirs(self.delivery_dir, exist_ok=True)
        except OSError:
            pass
        temp_zip = os.path.join(self.delivery_dir, f"livraison_{suffix}.zip")
        self.working_operation = MboxDelivery(temp_zip, temp_mbox)
        self.working_operation.add_context(
            self.server, self.account, self.selected_folder
        )
        self.working_operation.add_agent(f"{__appname__.capitalize()} {__version__}")
        self.working_thread = threading.Thread(
            target=self.working_operation.transform,
            kwargs={"progress_cb": self.progress_delivery},
            daemon=True,
        )
        self.working_thread.start()

    def progress_delivery(
        self, status: str, number: int, total: int, msg: str = ""
    ) -> None:
        """Manage the progress of the delivery thread"""
        if status == "start":
            self.progress_raz()
        elif status == "running":
            self.progress(status, number, total, msg)
        elif status == "error":
            self.enable_gui_after_work(
                [self.folders_btn, self.retrieve_btn, self.delivery_btn]
            )
            self.root.config(cursor="")
            try:
                os.remove(self.working_operation.dest_zip)
            except OSError:
                pass
            self.working_operation = None
            self.working_thread = None
            if len(msg) == 0:
                msg = (
                    "La livraison sous forme de ZIP n'a pas pu se faire.\n"
                    "Vous pouvez réessayer le cas échéant."
                )
            tkMessageBox.showerror("Erreur", msg)
        elif status == "complete":
            self.enable_gui_after_work(
                [self.folders_btn, self.retrieve_btn, self.delivery_btn]
            )
            self.root.config(cursor="")
            self.progress_raz()

            self.working_operation.clean()
            temp_zip = self.working_operation.dest_zip
            self.working_operation = None
            self.working_thread = None

            self.root.clipboard_clear()
            self.root.clipboard_append(temp_zip)
            msg = f"Livraison prête sur : [{temp_zip}]."
            tkMessageBox.showinfo("Information", msg)

    def on_click_folders_listbox(self, _event=None):
        """Handle selection in the folders list"""
        selection = _event.widget.curselection()
        if not selection:
            return
        index = selection[0]
        self.selected_folder = self.folders[index]

    def on_about_close(self, _event=None):
        """Action on closing the About pop-window"""
        if self.pop_about is not None:
            self.pop_about.destroy()
            self.pop_about = None
        self.about_btn.config(state="normal")

    def on_about(self, _event=None):
        """About function"""
        self.about_btn.config(state="disable")
        self.pop_about = show_textdialog(
            self.root,
            f"{__appname__.upper()} v{__version__}",
            "./assets/about_fr.txt",
            self.font_families,
            self.on_about_close,
        )

    def on_quit(self, _event=None):
        """Quit function"""
        self.prefs.set("WorkDir", self.work_dir)
        self.prefs.set("DeliveryDir", self.delivery_dir)
        self.prefs.set("LastServer", self.selected_server.get())
        self.prefs.set("LastLogin", self.login_entry.get().strip())
        self.prefs.save_prefs()

        # Wait 1 second to avoid race condition
        time.sleep(1)
        sys.exit(0)

    def on_info_password_close(self, _event=None):
        """Action on closing the Info password pop-window"""
        if self.pop_info_passwd is not None:
            self.pop_info_passwd.destroy()
            self.pop_info_passwd = None
        self.info_passwd_btn.config(state="normal")

    def on_info_password(self, _event=None):
        """Show info on applicative password"""
        self.info_passwd_btn.config(state="disable")
        self.pop_info_passwd = show_textdialog(
            self.root,
            f"{__appname__.upper()} v{__version__}",
            "./assets/password_fr.txt",
            self.font_families,
            self.on_info_password_close,
        )

    def on_show_hide(self, _event=None):
        """Show hide the password"""
        if self.password_hidden:
            self.password_entry.config(show="")
            self.hide_show_passwd_btn.config(image=self.hide_passwd_btn_img)
            self.password_hidden = False
        else:
            self.password_entry.config(show="*")
            self.hide_show_passwd_btn.config(image=self.show_passwd_btn_img)
            self.password_hidden = True

    def on_work_dir(self, _event=None):
        """Select a new workdir"""
        return_dir = tkFileDialog.askdirectory(
            parent=self, title="Répertoire de travail", initialdir=self.work_dir
        )
        if return_dir is None or len(return_dir) == 0:
            return
        self.work_dir = return_dir
        self.prefs.set("WorkDir", self.work_dir)
        self.fill_entry(self.work_dir_entry, self.work_dir)

    def on_delivery_dir(self, _event=None):
        """Select a new deliverydir"""
        return_dir = tkFileDialog.askdirectory(
            parent=self, title="Répertoire de livraison", initialdir=self.delivery_dir
        )
        if return_dir is None or len(return_dir) == 0:
            return
        self.delivery_dir = return_dir
        self.prefs.set("DeliveryDir", self.delivery_dir)
        self.fill_entry(self.delivery_dir_entry, self.delivery_dir)

    def fill_entry(self, entry, value: str):
        """Add value to a entry field"""
        entry.config(state="normal")
        entry.delete(0, tk.END)
        entry.insert(0, value)
        entry.config(state="readonly")

    def refresh_folders_list(self):
        """Refresh the list of folders"""
        folders_count = len(self.folders)
        self.folder_label.config(text=f"Liste des dossiers ({folders_count})")
        self.folders_listbox.delete(0, tk.END)
        for folder in self.folders:
            self.folders_listbox.insert("end", f"{folder}")

    def reset_folders_list(self):
        """Reset the list of folders"""
        self.folder_label.config(text="Liste des dossiers (0)")
        self.folders_listbox.delete(0, tk.END)

    def progress(self, status: str, number: int, total: int, msg: str = "") -> None:
        """Make the progress bar update to reflect the progress"""
        pct = int(100.0 * number / total) if total != 0 else 0
        self.progress_var.set(pct)
        if msg is None or len(msg) == 0:
            msg = f"{status}, {number}/{total} ({pct:d}%)"
        else:
            msg = f"{status}, {number}/{total} ({pct:d}%) [{msg}]"
        self.infolbl.config(text=msg)
        self.root.update()

    def progress_raz(self, msg: str = "") -> None:
        """RAZ the progress bar"""
        self.progress_var.set(0)
        self.infolbl.config(text=msg)
        self.root.update()

    def set_icon(self):
        """Set the icon depending on the OS"""
        if os.name == "nt":
            # Windows
            iconfile = resource_path("./images/email_gui.ico")
            self.root.wm_iconbitmap(default=iconfile)
        else:
            # Linux
            self.icon = tk.PhotoImage(
                file=resource_path("./images/Gartoon_apps_mail.svg.png")
            )
            self.root.wm_iconphoto(True, self.icon)

    def build_gui(self):
        """Build the GUI"""
        self.root.title(f"{__appname__.upper()} v{__version__}")
        self.set_icon()
        self.font_families = prepare_fonts(self.root, self._verbose)
        self.root.option_add(
            "*Font",
            f"\"{self.font_families['variable']}\" {self.font_families['size']}",
        )  # Courier, Times, Lucida
        self.root.option_add("*tearOff", "FALSE")
        self.grid(column=0, row=0, sticky="ew")
        self.grid_columnconfigure(0, weight=1, uniform="a")
        self.grid_columnconfigure(1, weight=1, uniform="a")
        self.grid_columnconfigure(2, weight=1, uniform="a")
        self.grid_columnconfigure(3, weight=1, uniform="a")
        self.grid_columnconfigure(4, weight=1, uniform="a")
        self.grid_columnconfigure(5, weight=1, uniform="a")
        row = 1
        # Toolbar
        # Folders button
        self.folders_btn, self._folders_btn_img = create_button(
            self,
            "Dossiers",
            "./images/Gartoon_apps_package_editors_32.png",
            0,
            row,
            self.on_folders,
        )
        self.folders_btn.config(underline=2)
        self.root.bind_all("<Control-d>", self.on_folders)

        # Retrieve button
        self.retrieve_btn, self._retrieve_btn_img = create_button(
            self,
            "Récupérer",
            "./images/Gartoon_actions_mail_get_32.png",
            1,
            row,
            self.on_retrieve,
        )
        self.retrieve_btn.config(underline=2)
        self.root.bind_all("<Control-r>", self.on_retrieve)
        # Delivery button
        self.delivery_btn, self._delivery_btn_img = create_button(
            self,
            "Livrer",
            "./images/Gartoon_actions_ark_addfile_32.png",
            2,
            row,
            self.on_delivery,
        )
        self.delivery_btn.config(underline=2)
        self.root.bind_all("<Control-l>", self.on_delivery)

        self.retrieve_btn.config(state="disabled")
        self.delivery_btn.config(state="disabled")
        # About button
        self.about_btn, self._about_btn_img = create_button(
            self,
            "À propos…",
            "./images/Gartoon_actions_messagebox_info_32.png",
            4,
            row,
            self.on_about,
        )
        # Quit button
        self.exit_btn, self._exit_btn_img = create_button(
            self,
            "Quitter",
            "./images/Gartoon_actions_exit_32.png",
            5,
            row,
            self.on_quit,
        )
        self.exit_btn.config(underline=2)
        self.root.bind_all("<Control-q>", self.on_quit)
        row += 1
        ttk.Separator(self, orient="horizontal").grid(
            column=0, row=row, columnspan=6, sticky="ew"
        )
        row += 1

        # Edits for server, account, folders
        self.selected_server = tk.StringVar()
        self.server_combo = create_combo(
            self, "Serveur :", self.selected_server, self.servers, 0, row
        )
        self.server_combo.bind("<<ComboboxSelected>>", self.on_server_changed)
        last_server = self.prefs.get("LastServer")
        if last_server is not None and len(last_server) != 0:
            self.server = self.known_servers.get_server(last_server)
            if self.server is not None:
                self.selected_server.set(last_server)
        self.work_dir_entry, self.work_dir_btn = create_entry_for_dir(
            self, "Répertoire de travail :", 3, row, self.on_work_dir
        )
        self.fill_entry(self.work_dir_entry, self.work_dir)
        row += 1
        self.login_entry = create_entry(self, "Login :", 0, row)
        last_login = self.prefs.get("LastLogin")
        if last_login is not None and len(last_login) != 0:
            self.fill_entry(self.login_entry, last_login)
        self.login_entry.config(state="normal")

        self.delivery_dir_entry, self.delivery_dir_btn = create_entry_for_dir(
            self, "Répertoire de livraison :", 3, row, self.on_delivery_dir
        )
        self.fill_entry(self.delivery_dir_entry, self.delivery_dir)
        row += 1

        self.password_entry = create_entry(self, "Mot de passe :", 0, row)
        self.password_entry.config(show="*")  # Password entry, mask the input
        self.password_entry.config(state="normal")
        self.password_hidden = True
        self.info_passwd_btn, self._info_passwd_btn_img = create_icon_button(
            self,
            "./images/OOjs_UI_icon_info_big_warning.svg.png",
            0,
            row,
            24,
            action=self.on_info_password,
        )
        self.hide_passwd_btn_img = tk.PhotoImage(
            file=resource_path("./images/OOjs_UI_icon_eyeClosed.svg.png")
        )
        self.hide_show_passwd_btn, self.show_passwd_btn_img = create_icon_button(
            self,
            "./images/OOjs_UI_icon_eye.svg.png",
            2,
            row,
            20,
            action=self.on_show_hide,
        )
        row += 1

        self.folder_label = tk.Label(
            self,
            text="Liste des dossiers (0)",
            font=(self.font_families["variable"], self.font_families["size"] + 2),
        )
        self.folder_label.grid(column=0, row=row, sticky="w")
        row += 1

        self.folders_listbox = tk.Listbox(
            self,
            selectmode="single",
            height=15,
            font=(self.font_families["mono"], self.font_families["size"]),
        )
        self.folders_listbox.grid(column=0, row=row, columnspan=3, sticky="ew")
        self.folders_listbox.bind("<<ListboxSelect>>", self.on_click_folders_listbox)
        scrollbar = tk.Scrollbar(self)
        # Attaching Listbox to Scrollbar,
        # since we need to have a vertical scroll we use yscrollcommand
        self.folders_listbox.config(yscrollcommand=scrollbar.set)
        # setting scrollbar command parameter to listbox.yview method
        # its yview because we need to have a vertical view
        scrollbar.config(command=self.folders_listbox.yview)
        scrollbar.grid(column=3, row=row, sticky="nsw")
        row += 1

        self.foldercounts_check_value = tk.BooleanVar(value=False)
        self.foldercounts_checkbox = tk.Checkbutton(
            self,
            text="avec nombre de mails",
            variable=self.foldercounts_check_value,
            onvalue=True,
            offvalue=False,
        )
        self.foldercounts_checkbox.grid(column=2, row=row, sticky="e")
        row += 1

        ttk.Separator(self, orient="horizontal").grid(
            column=0, row=row, columnspan=6, sticky="ew"
        )
        row += 1
        self.infolbl = tk.Label(
            self,
            text="",
            font=(self.font_families["variable"], self.font_families["size"], "bold"),
        )
        self.infolbl.grid(column=0, row=row, columnspan=6, sticky="ew")
        row += 1
        self.progressbar = ttk.Progressbar(variable=self.progress_var, maximum=100)
        self.progressbar.grid(column=0, row=row, columnspan=6, sticky="ew")
        row += 1

        # Make some space
        for child in self.winfo_children():
            child.grid_configure(padx=5, pady=5)


def parse():
    """Parse the command line"""
    parser = argparse.ArgumentParser(
        description="Programme de fourniture de courriels par IMAP"
    )
    parser.add_argument(
        "-log",
        "--loglevel",
        default="warning",
        help="Défini le niveau de log. Exemple --loglevel debug, default=warning",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="indique si le programme doit écrire des informations",
    )

    return parser.parse_args()


def main():
    """Main function"""
    args = parse()
    logging.basicConfig(level=args.loglevel.upper())

    # Affichage de l'IHM et boucle
    root = tk.Tk()
    my_gui = DonateGui(root, verbose=args.verbose)
    my_gui.verbose = args.verbose
    logger.debug("Launch GUI")
    # This ensures application quits normally if user closes window
    root.protocol("WM_DELETE_WINDOW", my_gui.on_quit)
    root.mainloop()


if __name__ == "__main__":
    main()
