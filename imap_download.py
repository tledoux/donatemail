# -*- coding: utf-8 -*-
"""
Module to handle the download of mails from an IMAP server

RFCs : https://www.rfc-editor.org/rfc/rfc3501

UTF7 modified for names of folder/mailbox :
* https://datatracker.ietf.org/doc/html/rfc2060.html#section-5.1.3
"""

import argparse
import glob
import imaplib
import io
import mailbox
import os
from dialog_utils import resource_path
from imap_server import ImapServers, ImapServer
from imap_account import ImapAccount, DEFAULT_ACCOUNT
from imap_folder import ImapFolder


class ImapDownload:
    """This class allows a download of mails"""

    def __init__(self, server: ImapServer, verbose: bool = False):
        self._server = server
        self._account = None
        self.folders = []
        self._verbose = verbose
        self._mboxfile = None

        self._mailconn = None

        self.last_error = None
        self.ret_code = True

    @property
    def server(self) -> ImapServer:
        """Getter for the server"""
        return self._server

    @property
    def account(self) -> ImapAccount:
        """Getter for the account"""
        return self._account

    @account.setter
    def account(self, value: ImapAccount):
        """Setter for the account"""
        self._account = value

    @account.deleter
    def account(self):
        """Deleter for the account"""
        del self._account

    @property
    def verbose(self) -> bool:
        """Getter for the verbose"""
        return self._verbose

    @verbose.setter
    def verbose(self, value: bool):
        """Setter for the verbose"""
        self._verbose = value

    @property
    def mboxfile(self) -> str:
        """Getter for the mboxfile"""
        return self._mboxfile

    @mboxfile.setter
    def mboxfile(self, value: str):
        """Setter for the mboxfile"""
        self._mboxfile = value

    @mboxfile.deleter
    def mboxfile(self):
        """Deleter for the mboxfile"""
        del self._mboxfile

    def login(self):
        """Log into the mailbox"""
        if self._mailconn is not None:
            return self._mailconn
        if self.account is None:
            raise ValueError("No account set")
        if self.verbose:
            print(f"Connect to {self.server}", flush=True)
        self._mailconn = imaplib.IMAP4_SSL(self.server.host, self.server.port)
        if self.verbose:
            print(f"Login with {self.account}", flush=True)
        self._mailconn.login(self.account.name, self.account.password)
        return self._mailconn

    def logout(self):
        """Logout"""
        if self._mailconn is None:
            return
        try:
            self._mailconn.logout()
        except imaplib.IMAP4.error as err:
            if self.verbose:
                print(f"ErrorType : {type(err).__name__}, Error : {err}")
        self._mailconn = None

    def _parse_folder(self, data):
        """Parse the LIST format.

        (\\Drafts) "/" MyDrafts
        (\\HasNoChildren) "/" "AirFrance"
        """
        flags, _, c = data.partition(" ")
        separator, _, name = c.partition(" ")
        return (flags, separator.replace('"', ""), name.replace('"', ""))

    def _test_flags(self, flags):
        """Test the flags for SPECIAL-USE.
        See https://datatracker.ietf.org/doc/html/rfc6154
        """
        ignore_flags = ["All", "Archive", "Drafts", "Flagged", "Junk", "Sent", "Trash"]
        for ignore in ignore_flags:
            if f"\\{ignore}" in flags:
                return True
        return False

    def list_folders(self, with_counts: bool = False, progress_cb=None):
        """List the folders of a mailbox"""
        self.last_error = None
        self.ret_code = True
        self.folders = []
        try:
            self.login()
            resp_code, data = self._mailconn.list()
            if resp_code != "OK":
                self.ret_code = False
                self.last_error = resp_code
                return
            msgs_count = 0
            f_count = 0
            max_folders = len(data)
            if progress_cb is not None:
                progress_cb("start", 0, max_folders)
            for mbox in data:
                flags, _, name = self._parse_folder(bytes.decode(mbox))
                if self._test_flags(flags):
                    continue
                folder = ImapFolder(name)
                if with_counts:
                    mycount, _msg = self.get_folder_count(folder)
                    if mycount == 0:
                        continue
                    msgs_count = msgs_count + mycount
                self.folders.append(folder)
                # print(f"{folder}", flush=True)
                f_count += 1
                # if with_counts and f_count > 20:
                #    break
                if progress_cb is not None and f_count % 5 == 0:
                    progress_cb(
                        "running",
                        f_count,
                        max_folders,
                        f"current: {folder.name}, msgs: {msgs_count}",
                    )
            if progress_cb is not None:
                total_folders = len(self.folders)
                progress_cb(
                    "complete",
                    total_folders,
                    total_folders,
                    f"total msgs: {msgs_count}",
                )
        except ValueError as err:
            self.last_error = f"Erreur de récupération : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )
        except imaplib.IMAP4.error as err:
            if self.verbose:
                print(f"ErrorType : {type(err).__name__}, Error : {err}")
            # imaplib.IMAP4.error: b'[AUTHENTICATIONFAILED] LOGIN Invalid credentials'
            if "[AUTHENTICATIONFAILED]" in str(err):
                self.last_error = (
                    "Erreur de connection: vérifiez le login et le mot de passe.\n\n"
                    f"{err}."
                )
            else:
                self.last_error = f"Erreur de récupération : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )

    def get_folder_count(self, folder: ImapFolder) -> tuple[int, str]:
        """Get the number of mails in the folder"""
        self.login()
        # Select the mailbox (in read-only mode), surround with "" to allow spaces and all
        resp, data = self._mailconn.select(f'"{folder.name_in_mutf7}"', readonly=True)
        self._mailconn.close()
        if resp != "OK":
            if self.verbose:
                print(f"Bad response {resp} when counting from {folder}")
            return (0, f"Bad response {resp} when counting from {folder}")
        mycount = int(data[0].decode())
        folder.count = mycount
        return (mycount, "")

    def get_folder(self, folder_name: str) -> ImapFolder:
        """Retrieve the ImapFolder by name from the list"""
        if self.folders is None or len(self.folders) == 0:
            return None
        for folder in self.folders:
            if folder.name == folder_name:
                return folder

    def get_mails(
        self, dest_dir: str, folder: ImapFolder = ImapFolder("INBOX"), progress_cb=None
    ):
        """Print the mails in the given folder"""
        self.last_error = None
        self.ret_code = True
        try:
            self.login()
            self._mailconn.select(f'"{folder.name_in_mutf7}"', readonly=True)
            # Get ALL message numbers
            resp, data = self._mailconn.search(None, "ALL")
            if resp != "OK":
                if self.verbose:
                    print(f"Bad response {resp} when retrieving mails from {folder}")
                raise ValueError(
                    f"Bad response {resp} when retrieving mails from {folder}"
                )
            numbers = data[0].split()
            max_msgs = len(numbers)
            count_msgs = 0
            if progress_cb is not None:
                progress_cb("start", count_msgs, max_msgs, f"folder: {folder.name}")
            for num in numbers:
                rv, data = self._mailconn.fetch(num, "(RFC822)")
                if rv != "OK":
                    if progress_cb is not None:
                        progress_cb(
                            "error",
                            count_msgs + 1,
                            max_msgs,
                            f"folder: {folder.name}, current: {int(num)}",
                        )
                    self.ret_code = False
                    self.last_error = f"folder: {folder.name}, current: {int(num)}"
                    return
                count_msgs += 1
                if progress_cb is not None and count_msgs % 5 == 0:
                    progress_cb(
                        "running",
                        count_msgs,
                        max_msgs,
                        f"folder: {folder.name}, current: {int(num)}",
                    )
                fname = os.path.join(dest_dir, f"m_{int(num):08d}.eml")
                # print(f'Writing message {fname}')
                with open(fname, "wb") as f:
                    f.write(data[0][1])
            self._mailconn.close()
            if progress_cb is not None:
                progress_cb("complete", count_msgs, max_msgs, f"folder: {folder.name}")
        except ValueError as err:
            self.last_error = f"Erreur de récupération : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )
        except imaplib.IMAP4.error as err:
            if self.verbose:
                print(f"ErrorType : {type(err).__name__}, Error : {err}")
            # imaplib.IMAP4.error: b'[AUTHENTICATIONFAILED] LOGIN Invalid credentials'
            if "[AUTHENTICATIONFAILED]" in str(err):
                self.last_error = (
                    "Erreur de connectison: vérifiez le login et le mot de passe.\n\n"
                    f"{err}."
                )
            else:
                self.last_error = f"Erreur de récupération : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )

    def get_mails_mbox(
        self, mboxfile: str, folder: ImapFolder = ImapFolder("INBOX"), progress_cb=None
    ):
        """Aggregate all the mails in the mbox"""
        self.last_error = None
        self.ret_code = True
        try:
            self._mboxfile = mboxfile
            self.login()
            self._mailconn.select(f'"{folder.name_in_mutf7}"', readonly=True)
            # Get ALL message numbers
            resp, data = self._mailconn.search(None, "ALL")
            if resp != "OK":
                if self.verbose:
                    print(f"Bad response {resp} when retrieving mails from {folder}")
                raise ValueError(
                    f"Bad response {resp} when retrieving mails from {folder}"
                )
            numbers = data[0].split()
            max_msgs = len(numbers)
            count_msgs = 0
            if progress_cb is not None:
                progress_cb("start", count_msgs, max_msgs, f"folder: {folder.name}")

            try:
                os.remove(mboxfile)
            except OSError:
                pass
            dest_mbox = mailbox.mbox(mboxfile, create=True)
            dest_mbox.lock()  # lock the mbox file
            try:
                for num in numbers:
                    rv, data = self._mailconn.fetch(num, "(RFC822)")
                    if rv != "OK":
                        if progress_cb is not None:
                            progress_cb(
                                "error",
                                count_msgs + 1,
                                max_msgs,
                                f"folder: {folder.name}, current: {int(num)}",
                            )
                        self.ret_code = False
                        self.last_error = f"folder: {folder.name}, current: {int(num)}"
                        return
                    # Wrap in BytesIO to force binary decoding
                    bstream = io.BytesIO(data[0][1])
                    dest_mbox.add(bstream)
                    count_msgs += 1
                    if count_msgs % 20 == 0:  # Flush every 20 messages
                        dest_mbox.flush()
                    if progress_cb is not None and count_msgs % 5 == 0:
                        progress_cb(
                            "running",
                            count_msgs,
                            max_msgs,
                            f"folder: {folder.name}, current: {int(num)}",
                        )
            finally:
                dest_mbox.close()  # close/unlock the mbox file
                try:
                    self._mailconn.close()
                except imaplib.IMAP4.error:
                    pass
            if progress_cb is not None:
                progress_cb("complete", count_msgs, max_msgs, f"folder: {folder.name}")
            self.ret_code = True
            self.last_error = ""
        except ValueError as err:
            self.last_error = f"Erreur de récupération : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )
        except imaplib.IMAP4.error as err:
            if self.verbose:
                print(f"ErrorType : {type(err).__name__}, Error : {err}")
            # imaplib.IMAP4.error: b'[AUTHENTICATIONFAILED] LOGIN Invalid credentials'
            if "[AUTHENTICATIONFAILED]" in str(err):
                self.last_error = (
                    "Erreur de connectison: vérifiez le login et le mot de passe.\n\n"
                    f"{err}."
                )
            else:
                self.last_error = f"Erreur de récupération : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )


def remove_eml_files(directory: str):
    """Remove all eml files in the directory"""
    files = glob.glob(f"{directory}/*.eml")
    for f in files:
        os.remove(f)


def parse():
    """Parse the command line"""
    parser = argparse.ArgumentParser(
        description="Programme de transformation d'email en eml vers mbox"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="tmp",
        help="Répertoire de sortie des fichiers EML",
    )

    parser.add_argument(
        "-s", "--server", default="Yahoo", help="Nom du serveur de WebMail"
    )

    parser.add_argument(
        "-u", "--user", required=True, help="utilisateur du mail (user:password)"
    )

    parser.add_argument(
        "-l", "--list", action="store_true", help="listing des dossiers du webmail"
    )

    parser.add_argument("-r", "--retrieve", help="récupération des mails du dossier")

    return parser.parse_args()


def progress(status: str, number: int, total: int, msg: str = "") -> None:
    """Function to print the progress of the retrieving of the information"""
    pct = int(100.0 * number / total) if total != 0 else 0
    if msg is None or len(msg) == 0:
        print(f"{status:<8}, {number}/{total} ({pct:2d}%)", flush=True)
    else:
        print(
            f"{status:<8}, {number}/{total} ({pct:2d}%) [{msg}]",
            flush=True,
        )


def main():
    """Main function for test purposes"""
    args = parse()
    servers = ImapServers()
    servers.read_from_json(resource_path("./assets/servers.json"))
    server = servers.get_server(args.server)
    user, password = args.user.split(":")
    account = ImapAccount(user, password)
    account = DEFAULT_ACCOUNT
    download = ImapDownload(server)
    download.account = account
    if args.list:
        download.list_folders(True, progress)
        if download.ret_code:
            for folder in sorted(download.folders):
                print(f"{folder}")
        else:
            print(f"ERROR: {download.last_error}")
    elif args.retrieve is not None:
        _fname, fext = os.path.splitext(args.output)
        if fext == ".mbox":
            if download.folders is not None and len(download.folders) != 0:
                download.get_mails_mbox(
                    args.output, download.get_folder(args.retrieve), progress
                )
            else:
                # Create a virtual folder for the retrieve
                folder = ImapFolder(args.retrieve)
                folder.name = args.retrieve  # To force the calculation the mutf7
                download.get_mails_mbox(args.output, folder, progress)
        else:
            os.makedirs(args.output, exist_ok=True)
            remove_eml_files(args.output)
            if download.folders is not None and len(download.folders) != 0:
                download.get_mails(
                    args.output, download.get_folder(args.retrieve), progress
                )
            else:
                # Create a virtual folder for the retrieve
                folder = ImapFolder(args.retrieve)
                folder.name = args.retrieve  # To force the calculation the mutf7
                download.get_mails(args.output, folder, progress)

    # download.get_mails()
    download.logout()


if __name__ == "__main__":
    main()
