# -*- coding: utf-8 -*-
"""Module to keep the details of a download"""

import argparse
import datetime
import json
import os

from imap_account import ImapAccount
from imap_folder import ImapFolder
from imap_server import ImapServer

DEFAULT_TIMEOUT = 10
DEFAULT_THRESHOLD = 2000


class DownloadContext:
    """Class to store the context of a download"""

    def __init__(self):
        self._agent = None
        self._imap_server = None
        self._imap_account = None
        self._imap_folder = None
        self._year_since = None
        self._year_before = None
        self._mbox = None
        self._timeout = DEFAULT_TIMEOUT
        self._threshold = DEFAULT_THRESHOLD

    @property
    def agent(self) -> str:
        """Getter to agent"""
        return self._agent

    @agent.setter
    def agent(self, agent: str):
        """Add agent information"""
        self._agent = agent

    @property
    def server(self) -> ImapServer:
        """Getter to imap_server"""
        return self._imap_server

    @property
    def account(self) -> ImapAccount:
        """Getter to imap_account"""
        return self._imap_account

    def add_context(
        self,
        server: ImapServer,
        account: ImapAccount,
    ):
        """Add information about the context of the download"""
        self._imap_server = server
        self._imap_account = account

    @property
    def folder(self) -> ImapFolder:
        """Getter for the folder"""
        return self._imap_folder

    @folder.setter
    def folder(self, value: ImapFolder):
        """Setter for the folder"""
        self._imap_folder = value

    @folder.deleter
    def folder(self):
        """Deleter for the folder"""
        del self._imap_folder

    @property
    def mbox(self) -> str:
        """Getter to mbox"""
        return self._mbox

    @mbox.setter
    def mbox(self, value: str):
        """Setter to mbox"""
        self._mbox = value

    def add_years(self, year_since: int = None, year_before: int = None):
        """Setter for date criteria"""
        self._year_since = year_since
        self._year_before = year_before

    def show_years(self) -> str:
        """Generate interval of years"""
        interval = None
        if self._year_since is not None and self._year_before is not None:
            interval = f"[{self._year_since or ''}-{self._year_before or ''}]"
        return interval

    @property
    def timeout(self) -> int:
        """Getter for the timeout in minutes"""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int):
        """Setter for the tiemout in minutes"""
        self._timeout = value

    @property
    def threshold(self) -> int:
        """Getter for the threshold"""
        return self._threshold

    @threshold.setter
    def threshold(self, value: int):
        """Setter for the threshold"""
        self._threshold = value

    def to_dict(self):
        """Transform the object in a dictionnary"""
        info = {}
        info["agent"] = self.agent or ""
        if self._imap_server is not None:
            info["server"] = self._imap_server.to_dict()
        if self._imap_account is not None:
            info["account"] = self._imap_account.to_dict()
        if self._imap_folder is not None:
            info["folder"] = self._imap_folder.to_dict()
        if self._year_since is not None or self._year_before is not None:
            info["scope"] = {}
            if self._year_since is not None:
                info["scope"]["year_begin"] = self._year_since
            if self._year_before is not None:
                info["scope"]["year_end"] = self._year_before
        info["mbox"] = os.path.basename(self._mbox)
        info["timeout"] = self._timeout
        info["threshold"] = self._threshold
        return info

    @classmethod
    def from_dict(cls, dct):
        """Create a DownloadDetail instance from a JSON manifest"""
        if "mbox" not in dct:
            return dct
        context = DownloadContext()
        context.agent = dct.get("agent", "")
        server = ImapServer.from_dict(dct["server"]) if "server" in dct else None
        account = ImapAccount.from_dict(dct["account"]) if "account" in dct else None
        context.add_context(server, account)
        context.folder = (
            ImapFolder.from_dict(dct["folder"]) if "folder" in dct else None
        )
        if "scope" in dct:
            context._year_since = (
                dct["scope"]["year_begin"] if "year_begin" in dct["scope"] else None
            )
            context._year_before = (
                dct["scope"]["year_end"] if "year_end" in dct["scope"] else None
            )
        context.mbox = dct["mbox"]
        context._timeout = dct.get("timeout", DEFAULT_TIMEOUT)
        context._threshold = dct.get("threshold", DEFAULT_THRESHOLD)
        return context

    def generate_bagit_info(self, with_desc: bool = True) -> str:
        """Generate a bagit-info.txt manifest for the delivery"""
        content = ""
        if self._agent is not None:
            content += f"Bag-Software-Agent: {self._agent}\n"
        content += f"Bagging-Date: {datetime.date.today().isoformat()}\n"
        if self._imap_server is not None:
            content += f"Source-Organization: {self._imap_server.name}\n"
        if self._imap_account is not None:
            content += f"Contact-Email: {self._imap_account.name}\n"
        if with_desc and self._imap_folder is not None:
            desc = f"Mails from folder '{self._imap_folder.name}'"
            if self._year_since is not None or self._year_before is not None:
                interval = " in the years {self.show_years()}"
                desc += interval
            content += f"External-Description: {desc}\n"
        return content

    @classmethod
    def make_dummy(cls, mbox: str = "test.mbox"):
        """Create a dummy context for test purposes"""
        context = DownloadContext()
        context.agent = "TestAgent 0.1"
        context.add_context(
            ImapServer("Yahoo", "imap.mail.yahoo.com"),
            ImapAccount("example@example.org", ""),
        )
        context.mbox = mbox
        context.folder = ImapFolder("test")
        return context


def parse():
    """Parse the command line"""
    parser = argparse.ArgumentParser(
        description="Programme de création d'un manifest de récupération d'une mbox"
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Fichier de sortie en json",
    )

    parser.add_argument(
        "-i",
        "--input",
        help="Fichier json de description",
    )

    parser.add_argument(
        "-m", "--mbox", default="test.mbox", help="Fichier mbox à packager"
    )

    return parser.parse_args()


def main():
    """Main function for test purposes"""
    args = parse()
    if args.input is not None:
        with open(args.input, "r", encoding="utf-8") as json_fd:
            context = json.load(json_fd, object_hook=DownloadContext.from_dict)
    else:
        context = DownloadContext.make_dummy(args.mbox)
    print(context.generate_bagit_info())
    if args.output is not None:
        json_str = context.generate_manifest()
        print(json_str)
        with open(args.output, "w", encoding="utf-8") as json_fd:
            print(json_str, file=json_fd)


if __name__ == "__main__":
    main()
