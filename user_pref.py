# -*- coding: utf-8 -*-
"""Module to handle user preferences"""

from pathlib import Path
import json
import os


class UserPreferences:
    """This class hold the information of user preferecnes"""

    def __init__(self, appname: str):
        """Initiate class"""
        self._appname = appname
        if os.name == "nt":
            self.dir_app = f"{Path.home()}/AppData/Roaming/{appname}"
        else:
            self.dir_app = f"{Path.home()}/.config/{appname}"
        os.makedirs(self.dir_app, exist_ok=True)
        self.pref_file = f"{self.dir_app}/{appname}.pref"
        self.user_pref = {}
        self.load_prefs()

    def load_prefs(self):
        """Load the preferences from the .pref file"""
        if os.path.exists(self.pref_file):
            with open(self.pref_file, "r", encoding="utf-8") as in_file:
                self.user_pref = json.load(in_file)

    def save_prefs(self):
        """Save the preferences to the .pref file"""
        os.makedirs(self.dir_app, exist_ok=True)
        with open(self.pref_file, "w", encoding="utf-8") as out_file:
            json.dump(self.user_pref, out_file)

    def get(self, pref: str) -> str:
        """Get a specific user preference"""
        return self.user_pref.get(pref, None)

    def set(self, pref: str, value: str) -> None:
        """Set a specific user preference"""
        self.user_pref[pref] = value
