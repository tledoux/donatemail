# -*- coding: utf-8 -*-
"""
Module to handle the download of mails from an IMAP server

RFCs : https://www.rfc-editor.org/rfc/rfc3501

UTF7 modified for names of folder/mailbox :
* https://datatracker.ietf.org/doc/html/rfc2060.html#section-5.1.3
"""

import argparse
import datetime
import glob
import imaplib
import io
import mailbox
import os
import re
import socket
import time

from dialog_utils import resource_path
from download_context import DownloadContext
from download_result import DownloadResult
from imap_server import ImapServers, ImapServer
from imap_account import ImapAccount, DEFAULT_ACCOUNT
from imap_folder import ImapFolder


class ImapDownload:
    """This class allows a download of mails"""

    def __init__(self, server: ImapServer, account: ImapAccount, verbose: bool = False):
        self._context = DownloadContext()
        self._context.add_context(server, account)
        self._result = DownloadResult()
        self._result.context = self._context

        self.folders = []
        self._verbose = verbose

        self._mailconn = None

        self.last_error = None
        self.ret_code = True

    @property
    def context(self) -> DownloadContext:
        """Getter for the context of the download"""
        return self._context

    @property
    def result(self) -> DownloadResult:
        """Getter for the result of the download"""
        return self._result

    @property
    def folder(self) -> ImapFolder:
        """Getter for the folder"""
        return self.context.folder

    @folder.setter
    def folder(self, value: ImapFolder):
        """Setter for the folder"""
        self.context.folder = value

    @folder.deleter
    def folder(self):
        """Deleter for the folder"""
        del self.context.folder

    @property
    def timeout(self) -> int:
        """Getter for the timeout in minutes"""
        return self.context.timeout

    @timeout.setter
    def timeout(self, value: int):
        """Setter for the tiemout in minutes"""
        self.context.timeout = value

    @property
    def threshold(self) -> int:
        """Getter for the threshold"""
        return self.context.threshold

    @threshold.setter
    def threshold(self, value: int):
        """Setter for the threshold"""
        self.context.threshold = value

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
        return self.context.mbox

    @mboxfile.setter
    def mboxfile(self, value: str):
        """Setter for the mboxfile"""
        self.context.mbox = value

    @mboxfile.deleter
    def mboxfile(self):
        """Deleter for the mboxfile"""
        del self.context.mbox

    def login(self):
        """Log into the mailbox"""
        if self._mailconn is not None:
            return self._mailconn
        if self.context.account is None:
            raise ValueError("No account set")
        self._log(f"Connect to {self.context.server}")
        self._mailconn = imaplib.IMAP4_SSL(
            self.context.server.host, self.context.server.port
        )
        sock = self._mailconn.socket()
        sock.settimeout(60 * self.timeout)
        self._log(f"Login with {self.context.account}")
        self._mailconn.login(self.context.account.name, self.context.account.password)
        return self._mailconn

    def logout(self):
        """Logout"""
        if self._mailconn is None:
            return
        try:
            self._mailconn.logout()
        except imaplib.IMAP4.error as err:
            self._log(f"ErrorType : {type(err).__name__}, Error : {err}")
        self._mailconn = None

    def _parse_folder(self, data: str):
        """Parse the LIST format.

        (\\Drafts) "/" MyDrafts
        (\\HasNoChildren) "/" "AirFrance"
        (\\HasNoChildren \\UnMarked \\Junk) "/" Junk
        (\\HasNoChildren) "/" "ACM Queue"
        """
        # self._log(f"Parse folder [{data}]")
        folder_list_re = re.compile(r"\((.+)\) ([^ ]+) (.*)")
        match = re.search(folder_list_re, data)
        if not match:
            return ("", "/", "")
        return (
            match.group(1),  # flags
            match.group(2).replace('"', ""),  # hierarchy delimiter
            match.group(3).replace('"', ""),  # name
        )

    def _test_flags(self, flags):
        """Test the flags for SPECIAL-USE.
        See https://datatracker.ietf.org/doc/html/rfc6154
        """
        # self._log(f"Test flags for {flags}")
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
            for line in data:
                flags, _, name = self._parse_folder(bytes.decode(line))
                if self._test_flags(flags):
                    continue
                folder = ImapFolder(name)
                if with_counts:
                    mycount, _msg = self.get_folder_count(folder)
                    if mycount == 0:  # skip empty folders
                        continue
                    msgs_count = msgs_count + mycount
                self.folders.append(folder)
                # print(f"{folder}", flush=True)
                f_count += 1
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
        except socket.gaierror as err:
            self.last_error = f"Erreur de connexion : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )
        except imaplib.IMAP4.error as err:
            self._log(f"ErrorType : {type(err).__name__}, Error : {err}")
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
        # self._mailconn.close()
        if resp != "OK":
            err_msg = f"Bad response {resp} when counting from {folder}"
            self._log(err_msg)
            return (0, err_msg)
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
                err_msg = f"Bad response {resp} when retrieving mails from {folder}"
                self._log(err_msg)
                raise ValueError(err_msg)
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
        except socket.gaierror as err:
            self.last_error = f"Erreur de connexion : {err}."
            self.ret_code = False
            if progress_cb is not None:
                progress_cb(
                    "error",
                    0,
                    0,
                    self.last_error,
                )
        except imaplib.IMAP4.error as err:
            self._log(f"ErrorType : {type(err).__name__}, Error : {err}")
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

    def _clean_mbox(self):
        try:
            os.remove(self.mboxfile)
        except OSError:
            pass

    def _set_error(self, err_msg: str, num: int, total: int, progress_cb=None):
        self.ret_code = False
        self.last_error = err_msg
        if progress_cb is not None:
            progress_cb(
                "error",
                num,
                total,
                self.last_error,
            )

    def _reconnect(self, num: int, folder: ImapFolder = None, wait_seconds: int = 3):
        """
        Make a reconnection to the server every 'threshold' message
        after waiting for the given delay.
        """
        if num % self.threshold != 0:
            return
        self._log(
            f"Reconnect preventif: {num} with {self.threshold}, wait {wait_seconds}"
        )

        self.logout()
        # Wait to let the server rest
        time.sleep(wait_seconds)
        self.login()
        if folder is not None:
            self._mailconn.select(f'"{folder.name_in_mutf7}"', readonly=True)

    def _log(self, msg):
        info_msg = f"{datetime.datetime.now().isoformat(timespec='seconds')} - {msg}"
        self.result.add_log(info_msg)
        if self.verbose:
            print(info_msg, flush=True)

    def _fetch_mail(self, folder: ImapFolder, num: int, count_msgs: int):
        """Fetch one mail with reconnection if BYE or NO response"""
        self._reconnect(count_msgs + 1, folder)
        try:
            rv, data = self._mailconn.fetch(str(num), "(RFC822)")
        except imaplib.IMAP4.abort as err:
            # imply the connection should be reset and the command retried
            self._log(f"Reconnect from 'BYE': {num=}, {err=}")
            self._reconnect(0, folder)
            rv, data = self._mailconn.fetch(str(num), "(RFC822)")
        except TimeoutError as err:
            self._log(f"TimeoutError : {num=}, {err=}")
            raise

        if rv == "NO":
            # NO [b'[UNAVAILABLE] FETCH Server error - Please try again later']
            info_msg = data[0].decode()
            self._log(f"Reconnect from 'NO': {num}\n{info_msg}")
            self._reconnect(0, folder, wait_seconds=600)
            rv, data = self._mailconn.fetch(str(num), "(RFC822)")
        return rv, data

    def _build_search_string(self, year_since: int = None, year_before: int = None):
        if year_since is None:
            if year_before is None:
                return "ALL"
            else:
                return f'(SENTBEFORE "31-Dec-{year_before}")'
        else:
            if year_before is None:
                return f'(SENTSINCE "01-Jan-{year_since}")'
            else:
                return f'(SENTSINCE "01-Jan-{year_since}" SENTBEFORE "31-Dec-{year_before}")'

    def get_mails_mbox(
        self,
        mboxfile: str,
        folder: ImapFolder = ImapFolder("INBOX"),
        year_since: int = None,
        year_before: int = None,
        progress_cb=None,
    ):
        """Aggregate all the mails in the mbox"""
        self.last_error = None
        self.ret_code = True
        self.result.start()
        self.context.folder = folder
        self.context.add_years(year_since, year_before)
        self.context.mbox = mboxfile
        try:
            self.mboxfile = mboxfile
            self.login()
            self._mailconn.select(f'"{folder.name_in_mutf7}"', readonly=True)
            # Get ALL message numbers
            # SENTSINCE 1-Jan-2003 SENTBEFORE 31-Dec-2004
            # self._mailconn.search(None, '(SENTSINCE "01-Jan-2003" SENTBEFORE "31-Dec-2004")')
            search = self._build_search_string(year_since, year_before)
            resp, data = self._mailconn.search(None, search)
            if resp != "OK":
                self._log(f"Bad response {resp} when retrieving mails from {folder}")
                raise ValueError(
                    f"Bad response {resp} when retrieving mails from {folder}"
                )
            numbers = data[0].split()
            max_msgs = len(numbers)
            count_msgs = 0
            if progress_cb is not None:
                progress_cb("start", count_msgs, max_msgs, f"folder: {folder.name}")

            self._clean_mbox()
            dest_mbox = mailbox.mbox(self.mboxfile, create=True)
            dest_mbox.lock()  # lock the mbox file
            try:
                for num in numbers:
                    # Fetch one mail with reconnection if BYE or NO response
                    rv, data = self._fetch_mail(folder, int(num), count_msgs)
                    if rv == "NO":
                        # This record is unavailable skip it
                        self._reconnect(0, folder, wait_seconds=2)
                        self._log(f"Skipping record {int(num)}")
                        self.result.add_skip_mail(int(num))
                        dest_mbox.flush()
                        if progress_cb is not None:
                            progress_cb(
                                "warning",
                                count_msgs,
                                max_msgs,
                                f"folder: {folder.name}, SKIP: {int(num)}",
                            )
                        continue

                    if rv != "OK":
                        info_msg = data[0].decode()
                        err_msg = f"folder: {folder.name}, current: {int(num)}, return: {rv}\n{info_msg}"
                        self._log(err_msg)
                        self._log(info_msg)

                        self._set_error(
                            err_msg,
                            count_msgs + 1,
                            max_msgs,
                            progress_cb,
                        )
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
                if self._mailconn is not None:
                    try:
                        self._mailconn.close()
                    except (imaplib.IMAP4.error, OSError):
                        # raise OSError("cannot read from timed out object")
                        pass
            self.result.end(count_msgs, max_msgs)
            if progress_cb is not None:
                progress_cb("complete", count_msgs, max_msgs, f"folder: {folder.name}")
            self.ret_code = True
            self.last_error = ""
        except ValueError as err:
            self._set_error(f"Erreur de récupération : {err}.", 0, 0, progress_cb)
        except TimeoutError as err:
            self._set_error(f"Delai de connexion dépassé : {err}.", 0, 0, progress_cb)
        except socket.gaierror as err:
            self._set_error(f"Erreur de connexion : {err}.", 0, 0, progress_cb)
        except imaplib.IMAP4.error as err:
            self._log(f"ErrorType : {type(err).__name__}, Error : {err}")
            # imaplib.IMAP4.error: b'[AUTHENTICATIONFAILED] LOGIN Invalid credentials'
            if "[AUTHENTICATIONFAILED]" in str(err):
                err_msg = (
                    "Erreur de connectison: vérifiez le login et le mot de passe.\n\n"
                    f"{err}."
                )
            else:
                err_msg = f"Erreur de récupération : {err}."
            self._set_error(err_msg, 0, 0, progress_cb)


def calculate_mbox_dest(outdir: str, folder: ImapFolder = ImapFolder("INBOX")) -> str:
    """Calculate the path of the mbox file and create the needed directories"""
    # Use modified UTF-7 to avoid interoperability issues in filenames
    name_mbox = f"{folder.name_in_mutf7}.mbox"
    path_mbox = os.path.join(outdir, name_mbox)
    dir_mbox = os.path.dirname(path_mbox)
    try:
        os.makedirs(dir_mbox, exist_ok=True)
    except OSError:
        pass
    return path_mbox


def calculate_json_dest(outdir: str, folder: ImapFolder = ImapFolder("INBOX")) -> str:
    """Calculate the path of the json file and create the needed directories"""
    # Use modified UTF-7 to avoid interoperability issues in filenames
    name_json = f"{folder.name_in_mutf7}.json"
    path_json = os.path.join(outdir, name_json)
    dir_json = os.path.dirname(path_json)
    try:
        os.makedirs(dir_json, exist_ok=True)
    except OSError:
        pass
    return path_json


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

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="indique si le programme doit écrire des informations",
    )

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
    if args.user is None:
        account = DEFAULT_ACCOUNT
    else:
        user, password = args.user.split(":")
        account = ImapAccount(user, password)
    download = ImapDownload(server, args.verbose)
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
