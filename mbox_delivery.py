# -*- coding: utf-8 -*-
"""Module to create a delivery for a mbox"""

import argparse
import datetime
import hashlib
import json
import os
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

from imap_account import ImapAccount
from imap_folder import ImapFolder
from imap_server import ImapServer

CHUNK_SIZE = 16 * 1024 * 1024  # 16 Mio


def chunked(file, chunk_size: int):
    """Create a iterable from a reading of a file"""
    return iter(lambda: file.read(chunk_size), b"")


class MboxDelivery:
    """Class to create a delivery"""

    def __init__(self, dest_zip: str, src_mbox: str):
        self._dest_zip = dest_zip
        self._src_mbox = src_mbox
        self._agent = None
        self._imap_server = None
        self._imap_account = None
        self._imap_folder = None

    @property
    def dest_zip(self) -> str:
        """Getter to dest_zip"""
        return self._dest_zip

    @property
    def src_mbox(self) -> str:
        """Getter to src_mbox"""
        return self._src_mbox

    def add_agent(self, agent: str):
        """Add agent information"""
        self._agent = agent

    def add_context(
        self,
        server: ImapServer,
        account: ImapAccount,
        folder: ImapFolder,
    ):
        """Add information about the context of the delivery"""
        self._imap_server = server
        self._imap_account = account
        self._imap_folder = folder

    def generate_manifest(self):
        """Generate a JSON manifest for the delivery"""
        info = {}
        info["date"] = datetime.datetime.now().isoformat()
        if self._imap_server is not None:
            info["server"] = self._imap_server.to_dict()
        if self._imap_account is not None:
            info["account"] = self._imap_account.name
        if self._imap_folder is not None:
            info["folder"] = self._imap_folder.to_dict()
        info["mbox"] = os.path.basename(self._src_mbox)
        return json.dumps(info, indent=2)

    def generate_bagit_info(self) -> str:
        """Generate a bagit-info.txt manifest for the delivery"""
        content = ""
        if self._agent is not None:
            content += f"Bag-Software-Agent: {self._agent}\n"
        content += f"Bagging-Date: {datetime.date.today().isoformat()}\n"
        if self._imap_server is not None:
            content += f"Source-Organization: {self._imap_server.name}\n"
        if self._imap_account is not None:
            content += f"Contact-Email: {self._imap_account.name}\n"
        if self._imap_folder is not None:
            content += (
                f"External-Description: Mails from folder {self._imap_folder.name}\n"
            )
        return content

    def create_regular_zipinfo(self, name):
        """Prepare a ZipInfo for a regular file"""
        info = ZipInfo(
            name,
            date_time=datetime.datetime.now().timetuple()[:6],
        )
        info.external_attr = 0o100666 << 16  # rw for all
        return info

    def add_content_by_chunk(self, zip_archive: ZipFile, progress_cb=None):
        """
        Add the mbox content to the ZIP with md5 calculation.
        """
        # data with md5 calculation
        data_name = "data/" + os.path.basename(self._src_mbox)
        mbox_size = os.path.getsize(self._src_mbox)
        info_data = ZipInfo.from_file(self._src_mbox, data_name)
        info_data.compress_type = ZIP_DEFLATED
        md5sum = hashlib.md5()
        read_size = 0
        with open(self._src_mbox, "rb") as fmbox:
            with zip_archive.open(info_data, mode="w", force_zip64=True) as zf:
                for chunk in chunked(fmbox, CHUNK_SIZE):
                    md5sum.update(chunk)
                    zf.write(chunk)
                    read_size += len(chunk)
                    # Update progress
                    if progress_cb is not None:
                        progress_cb(
                            "running",
                            read_size,
                            mbox_size,
                            f"current: {data_name}",
                        )
        data_md5 = md5sum.hexdigest()
        return data_md5

    def transform(self, progress_cb=None) -> int:
        """Make the zip, add the manifest and the mbox file"""
        try:
            count = 0
            data_name = "data/" + os.path.basename(self._src_mbox)
            mbox_size = os.path.getsize(self._src_mbox)
            if progress_cb is not None:
                progress_cb("start", 0, mbox_size)

            with ZipFile(self._dest_zip, "w") as zip_archive:
                # header bagit.txt
                zip_archive.writestr(
                    self.create_regular_zipinfo("bagit.txt"),
                    "BagIt-Version: 1.0\nTag-File-Character-Encoding: UTF-8\n",
                    compress_type=ZIP_STORED,
                )
                count += 1

                # data with md5 calculation
                data_md5 = self.add_content_by_chunk(zip_archive, progress_cb)
                count += 1

                # manifest for md5 checksums
                zip_archive.writestr(
                    self.create_regular_zipinfo("manifest-md5.txt"),
                    f"{data_md5} {data_name}\n",
                    compress_type=ZIP_STORED,
                )
                count += 1

                # info about the bag
                content = self.generate_bagit_info()
                zip_archive.writestr(
                    self.create_regular_zipinfo("bagit-info.txt"),
                    content.encode("utf8"),
                    compress_type=ZIP_STORED,
                )
                count += 1
            if progress_cb is not None:
                progress_cb(
                    "complete",
                    mbox_size,
                    mbox_size,
                )
        except OSError as err:
            if progress_cb is not None:
                progress_cb("error", 0, 0, f"Erreur : {err}")
        return count

    def clean(self) -> None:
        """Remove all the source files"""
        try:
            os.remove(self._src_mbox)
        except OSError:
            pass


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


def parse():
    """Parse the command line"""
    parser = argparse.ArgumentParser(
        description="Programme de création d'un paquet de livraison contenant un mbox"
    )

    parser.add_argument(
        "-o",
        "--output",
        default="test.zip",
        help="Fichier de sortie en zip",
    )

    parser.add_argument(
        "-i", "--input", default="text.mbox", help="Fichier mbox à packager"
    )

    return parser.parse_args()


def main():
    """Main function for test purposes"""
    args = parse()
    transform = MboxDelivery(args.output, args.input)
    transform.add_context(
        ImapServer("Yahoo", "imap.mail.yahoo.com"),
        ImapAccount("example@example.org", ""),
        ImapFolder("test"),
    )
    transform.add_agent("TestAgent 0.1")
    count = transform.transform(progress)
    print(f"{count} fichiers packagés vers {args.output}")


if __name__ == "__main__":
    main()
