# -*- coding: utf-8 -*-
"""Module to handle the accounts"""


class ImapAccount:
    """This class hold the information on an imap account"""

    def __init__(self, name: str, password: str):
        """Initiate class"""
        self._name = name
        self._password = password

    @property
    def name(self) -> str:
        """Getter for name"""
        return self._name

    @property
    def password(self) -> str:
        """Getter for password"""
        return self._password

    @password.setter
    def password(self, value: str) -> None:
        """Setter for password"""
        self._password = value

    def __str__(self) -> str:
        """String representation"""
        return f"{self.name}"

    def to_dict(self):
        """Transform the object in a dictionnary"""
        return {"name": self.name}


DEFAULT_ACCOUNT = ImapAccount("test@example.org", "")
