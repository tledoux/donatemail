# -*- coding: utf-8 -*-
"""Module to keep the details of a download"""

import argparse
import datetime
import json

from download_context import DownloadContext


class DownloadResult:
    """Class to store the result of a download"""

    def __init__(self):
        self._context = None
        self._total_mails = 0
        self._start_datetime = None
        self._end_datetime = None
        self._download_mails = 0
        self._skip_mails = []
        self._logs = []

    def start(self):
        """Reset the result for a new download"""
        self.total_mails = 0
        self.start_datetime = datetime.datetime.now().isoformat(timespec="seconds")
        self.download_mails = 0
        self._skip_mails = []
        self._logs = []

    def end(self, total: int, count: int):
        """Stop the download"""
        self.end_datetime = datetime.datetime.now().isoformat(timespec="seconds")
        self.total_mails = total
        self.download_mails = count

    @property
    def context(self) -> str:
        """Getter to the context of the download"""
        return self._context

    @context.setter
    def context(self, value: DownloadContext):
        """Setter to context"""
        self._context = value

    @property
    def total_mails(self) -> int:
        """Getter for the total of mails"""
        return self._total_mails

    @total_mails.setter
    def total_mails(self, value: int):
        """Setter for the total of mails"""
        self._total_mails = value

    @property
    def download_mails(self) -> int:
        """Getter for the count of download mails"""
        return self._download_mails

    @download_mails.setter
    def download_mails(self, value: int):
        """Setter for the download of mails"""
        self._download_mails = value

    def add_skip_mail(self, number: int):
        """Add the sequence number of the skip mail"""
        self._skip_mails.append(number)

    def get_count_skip_mails(self):
        """Retrieve the number of skip mails"""
        return len(self._skip_mails)

    @property
    def logs(self) -> list[str]:
        """Getter for the logs"""
        return self._logs

    def add_log(self, log: str):
        """Add the log to th elogs"""
        self._logs.append(log)

    @property
    def start_datetime(self) -> str:
        """Getter for the starttime"""
        return self._start_datetime

    @start_datetime.setter
    def start_datetime(self, value: str):
        """Setter for the total of mails"""
        if self._end_datetime is None:
            self._end_datetime = value
        self._start_datetime = value

    @property
    def end_datetime(self) -> str:
        """Getter for the endtime"""
        return self._end_datetime

    def calculate_duration(self) -> str:
        """Calculate the time of processing"""
        if self._start_datetime is None or self._end_datetime is None:
            return "00:00:00"
        begin = datetime.datetime.fromisoformat(self._start_datetime)
        end = datetime.datetime.fromisoformat(self._end_datetime)
        delta = end - begin
        hours, rem = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"

    @end_datetime.setter
    def end_datetime(self, value: str):
        """Setter for the endtime"""
        if self._start_datetime is None:
            self._start_datetime = value
        self._end_datetime = value

    def generate_manifest(self):
        """Generate a JSON manifest for the download"""
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self):
        """Transform the object in a dictionnary"""
        info = {}
        info["date"] = datetime.datetime.now().isoformat(timespec="seconds")
        if self._context is not None:
            info["context"] = self._context.to_dict()
        if self._start_datetime is not None:
            info["timings"] = {
                "start": self._start_datetime,
                "end": self._end_datetime,
                "duration": self.calculate_duration(),
            }
        info["statistics"] = {
            "total": self._total_mails,
            "downloaded": self._download_mails,
            "skipped": self._skip_mails,
        }
        info["logs"] = self.logs
        return info

    @classmethod
    def from_dict(cls, dct):
        """Create a DownloadResult instance from a dictionnary"""
        if "context" not in dct:
            return dct
        result = DownloadResult()
        result._context = DownloadContext.from_dict(dct["context"])
        result._logs = dct.get("logs", [])
        stat = dct.get("statistics")
        if stat is not None:
            result._total_mails = stat["total"]
            result._download_mails = stat["downloaded"]
            result._skip_mails = stat["skipped"]
        timings = dct.get("timings")
        if timings is not None:
            result._start_datetime = timings["start"]
            result._end_datetime = timings["end"]
        return result

    def generate_bagit_info(self, oxum: str = None) -> str:
        """Generate a bagit-info.txt manifest for the delivery"""
        content = self._context.generate_bagit_info(with_desc=False)
        if self.context.folder is not None:
            desc = (
                f"{self.download_mails} mails from folder '{self.context.folder.name}'"
            )
            interval = self.context.show_years()
            if interval is not None:
                desc += " in the years {interval}"
            content += f"External-Description: {desc}\n"
        if oxum is not None:
            content += f"Payload-Oxum: {oxum}\n"
        return content

    @classmethod
    def make_dummy(cls, mbox: str = "test.mbox"):
        """Create a dummy result for test purposes"""
        result = DownloadResult()
        result.context = DownloadContext.make_dummy(mbox)
        result.start_datetime = "1900-01-01T12:00:00"
        result.end_datetime = "1900-01-02T18:20:00"
        result.total_mails = 8000
        result.download_mails = 7998
        result.add_skip_mail(234)
        result.add_skip_mail(235)
        result.add_log("1900-01-01 - Test 1")
        result.add_log("1900-01-01 - Test 2")
        result.add_log("1900-01-01 - Test 3")
        return result


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
            result = json.load(json_fd, object_hook=DownloadResult.from_dict)
    else:
        result = DownloadResult.make_dummy(args.mbox)
    print(result.generate_bagit_info())
    if args.output is not None:
        json_str = result.generate_manifest()
        print(json_str)
        with open(args.output, "w", encoding="utf-8") as json_fd:
            print(json_str, file=json_fd)


if __name__ == "__main__":
    main()
