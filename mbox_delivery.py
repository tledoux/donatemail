# -*- coding: utf-8 -*-
"""Module to create a delivery for a mbox"""

import argparse
import datetime
import hashlib
import json
import os
import tempfile
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED, ZIP_STORED

from download_result import DownloadResult

CHUNK_SIZE = 16 * 1024 * 1024  # 16 Mio


def chunked(file, chunk_size: int):
    """Create a iterable from a reading of a file"""
    return iter(lambda: file.read(chunk_size), b"")


class MboxDelivery:
    """Class to create a delivery"""

    def __init__(self, dest_zip: str, src_mbox: str, src_json: str):
        self._dest_zip = dest_zip
        self._src_mbox = src_mbox
        self._src_json = src_json
        with open(src_json, "r", encoding="utf-8") as json_fd:
            self._result = json.load(json_fd, object_hook=DownloadResult.from_dict)

    @property
    def dest_zip(self) -> str:
        """Getter to dest_zip"""
        return self._dest_zip

    @property
    def src_mbox(self) -> str:
        """Getter to src_mbox"""
        return self._src_mbox

    @property
    def result(self) -> DownloadResult:
        """Getter to result"""
        return self._result

    @result.setter
    def result(self, value: DownloadResult):
        """Setter to result"""
        self._result = value

    def generate_manifest(self) -> str:
        """Generate a JSON manifest for the delivery"""
        info = self.result.to_dict()
        return json.dumps(info, indent=2)

    def generate_bagit_info(self, oxum: str = None) -> str:
        """Generate a bagit-info.txt manifest for the delivery"""
        content = self.result.generate_bagit_info(oxum)
        return content

    def create_regular_zipinfo(self, name):
        """Prepare a ZipInfo for a regular file"""
        info = ZipInfo(
            name,
            date_time=datetime.datetime.now().timetuple()[:6],
        )
        info.external_attr = 0o100666 << 16  # rw for all
        return info

    def add_content_by_chunk(
        self, zip_archive: ZipFile, is_data: bool = True, progress_cb=None
    ) -> tuple[str, str]:
        """
        Add the mbox content to the ZIP with md5 calculation.
        """
        # data with md5 calculation
        if is_data:
            file_path = self._src_mbox
            info_name = "data/" + os.path.basename(file_path)
        else:
            file_path = self._src_json
            info_name = "metadata/" + os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        info_data = ZipInfo.from_file(file_path, info_name)
        info_data.compress_type = ZIP_DEFLATED
        md5sum = hashlib.md5()
        read_size = 0
        with open(file_path, "rb") as fmbox:
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
                            file_size,
                            f"current: {info_name}",
                        )
        data_md5 = md5sum.hexdigest()
        return info_name, data_md5

    def transform(self, progress_cb=None) -> int:
        """Make the zip, add the manifest and the mbox file"""
        try:
            count = 0
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
                data_name, data_md5 = self.add_content_by_chunk(
                    zip_archive, True, progress_cb
                )
                count += 1

                # manifest for md5 checksums
                zip_archive.writestr(
                    self.create_regular_zipinfo("manifest-md5.txt"),
                    f"{data_md5} {data_name}\n",
                    compress_type=ZIP_STORED,
                )
                count += 1

                # metatdata with md5 calculation
                metadata_name, metadata_md5 = self.add_content_by_chunk(
                    zip_archive, False, progress_cb
                )
                count += 1

                # manifest for md5 checksums
                zip_archive.writestr(
                    self.create_regular_zipinfo("tagmanifest-md5.txt"),
                    f"{metadata_md5} {metadata_name}\n",
                    compress_type=ZIP_STORED,
                )
                count += 1

                # info about the bag
                oxum = f"{os.path.getsize(self._src_mbox)}.1"
                content = self.generate_bagit_info(oxum)
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
            os.remove(self._src_json)
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

    parser.add_argument("-j", "--json", default="DUMMY", help="Fichier json à packager")

    return parser.parse_args()


def main():
    """Main function for test purposes"""
    args = parse()
    jsonfile = args.json
    if args.json == "DUMMY":
        # build a minimal json file
        result = DownloadResult.make_dummy(args.mbox)
        json_str = result.generate_manifest()
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        ) as json_fd:
            jsonfile = json_fd.name
            print(json_str, file=json_fd)

    transform = MboxDelivery(args.output, args.input, jsonfile)
    count = transform.transform(progress)
    if args.json == "DUMMY":
        os.unlink(jsonfile)
    print(f"{count} fichiers packagés vers {args.output}")


if __name__ == "__main__":
    main()
