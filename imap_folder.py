# -*- coding: utf-8 -*-
"""
Module to handle the folders of a mailbox

Be aware in IMAP protocol folder names are modified UTF-7 encoded.

See:
* https://datatracker.ietf.org/doc/html/rfc2060.html#section-5.1.3

"""
from mutf7 import decode_mutf7, encode_mutf7


class ImapFolder:
    """This class hold the information on an imap folder"""

    def __init__(self, name, count=-1):
        """Initiate class with info from IMAP LIST"""
        self._name_in_mutf7 = name
        self._name = decode_mutf7(name)
        self._count = count

    @property
    def name(self) -> str:
        """Getter for name"""
        return self._name

    @name.setter
    def name(self, value: str):
        """Setter for name without decoding"""
        self._name = value
        self._name_in_mutf7 = encode_mutf7(self._name)

    @property
    def name_in_mutf7(self) -> str:
        """Getter for name in modified UTF-7"""
        return self._name_in_mutf7

    @property
    def count(self) -> int:
        """Getter for count"""
        return self._count

    @count.setter
    def count(self, value: int):
        """Setter for count"""
        self._count = value

    def __lt__(self, other):
        """Less-than function to allow sorting"""
        if self.count != -1:
            # SORT BY DESC COUNT
            return self.count >= other.count
        # SORT BY NAME
        return self._name < other._name

    def __str__(self) -> str:
        """String representation"""
        if self.count == -1:
            return f"{self.name:<30}"
        return f"{self.name:<30} ({self.count:5d})"

    def to_dict(self):
        """Transform the object in a dictionnary"""
        if self.count != -1:
            return {"name": self.name, "count": self.count}
        else:
            return {"name": self.name}
