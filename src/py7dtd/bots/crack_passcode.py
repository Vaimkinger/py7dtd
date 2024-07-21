#!/usr/bin/env python3

import argparse
import logging
import string
import threading
import time
from datetime import timedelta
from itertools import product
from os import path

import pyperclip
import win32com.client as comclt
from PIL import ImageGrab
from py7dtd.constants import APPLICATION_WINDOW_NAME

from iocontroller.keymouse.commands_controller import (
    MoveMouseAbsolute,
    RightMouseClick,
)
from iocontroller.keymouse.key_watcher import KeyWatcher
from iocontroller.window.window_handler import (
    get_absolute_window_center,
    select_window,
)

logging.getLogger(__name__)
logging.root.setLevel(logging.INFO)


class CrackPasscode(object):
    def __init__(self, args):
        self.stopped = False
        self.args = args
        self.init_args()

    def init_args(self) -> None:
        if self.args.brute and self.args.dict:
            logging.error(
                "Error: only one method can be selected. Available are: `brute`, `dict`."
            )
            exit()

        if self.args.dict and not path.exists(self.args.dictpath):
            logging.error(
                "Error: the specified dictionary file does not exist."
            )
            exit()

        if not self.args.brute and not self.args.dict:
            logging.warning(
                "Warning: a method has not been selected."
                + " Available are: `brute`, `dict`. `dict` has been selected by default."
            )
            self.args.dict = True

        self.delay = self.args.delay / 1000
        self.last_codes = []
        self.attempts = 0

    def watch_keys(self) -> None:
        self.watcher = KeyWatcher(stop_func=self.stop)
        self.watcher.start()

    def start(self) -> None:
        # Select the application window
        try:
            self.window = select_window(APPLICATION_WINDOW_NAME)
        except Exception as err:
            logging.error(str(err))
            return
        self.pointer_center = get_absolute_window_center(
            int(self.window.left),
            int(self.window.top),
            int(self.window.width),
            int(self.window.height),
        )

        # Compute grey pixel position in "SUBMIT" button box
        self.grey_submit_left = int(self.window.left) + int(
            self.window.width * (1300 / 2560)
        )
        self.grey_submit_top = int(self.window.top) + int(
            self.window.height * (840 / 1497)
        )

        MoveMouseAbsolute(self.pointer_center[0], self.pointer_center[1])

        # Spawn the key_watcher thread
        self.watcher_thread = threading.Thread(target=self.watch_keys, args=())
        # Daemon = True -> kill it when main thread terminates
        self.watcher_thread.setDaemon(True)
        self.watcher_thread.start()

        # Init win32com to inject keys
        self.wsh = comclt.Dispatch("WScript.Shell")
        self.wsh.AppActivate(APPLICATION_WINDOW_NAME)

        self.tries = 0
        self.start_time = time.time()

        logging.info("Press ESC key to stop.")

        if self.args.brute:
            self.crack_brute()

        if self.args.dict:
            self.crack_dict()

        logging.info("Crack passcode stopped")

    def crack_brute(self) -> None:
        allowed_chars = []
        if self.args.digits:
            allowed_chars += string.digits
        if self.args.lower:
            allowed_chars += string.ascii_lowercase
        if self.args.upper:
            allowed_chars += string.ascii_uppercase
        if self.args.special:
            allowed_chars += string.punctuation
        if self.args.lowercyrillic:
            allowed_chars += list("абвгдеёжзийклмнопстуфхцчшщъыьэюя")
        if self.args.uppercyrillic:
            allowed_chars += list("АБВГДЕЁЖЗИЙКЛМНОПСТУФХЦЧШЩЪЫЬЭЮЯ")

        if len(allowed_chars) == 0:
            logging.warning(
                "Warning: empty characters set. `digits` and `lower` have been selected by default."
            )
            allowed_chars += string.digits + string.ascii_lowercase

        logging.info("Brute force attack started")
        for length in range(self.args.min, self.args.max + 1):
            to_attempt = product(allowed_chars, repeat=length)

            for attempt in to_attempt:
                passcode = "".join(attempt)
                self.last_codes.append(passcode)
                if len(self.last_codes) > 5:
                    self.last_codes.pop(0)
                self.try_passcode(passcode)
                self.attempts += 1
                if self.attempts % 100 == 0:
                    logging.info(
                        f"Total processed pass codes: {str(self.attempts)}"
                        + f" | Elapsed time: {str(timedelta(seconds=time.time() - self.start_time))}"
                    )
                if self.check_stopped():
                    logging.info(f"Last tried passcode: {passcode}")
                    return

    def crack_dict(self) -> None:
        logging.info("Dictionary attack started")
        line_count = 0
        if self.args.resumedict:
            logging.info(
                f"Start reading dictionary from line {str(self.args.resumedict)}"
            )
        with open(self.args.dictpath, "r", encoding="utf8") as dict_file:
            for line in dict_file:
                line_count += 1
                if self.args.resumedict and line_count < self.args.resumedict:
                    continue
                passcode = line.strip()
                self.last_codes.append(passcode)
                if len(self.last_codes) > 5:
                    self.last_codes.pop(0)
                self.try_passcode(passcode)
                self.attempts += 1
                if self.attempts % 100 == 0:
                    logging.info(
                        f"Total processed pass codes: {str(self.attempts + self.args.resumedict)}"
                        + f" | Elapsed time: {str(timedelta(seconds=time.time() - self.start_time))}"
                    )
                if self.check_stopped():
                    logging.info(
                        f"Last tried passcode (line {str(line_count)}): {passcode}"
                    )
                    return

    # documentation: https://ss64.com/vb/sendkeys.html
    def try_passcode(self, passcode) -> None:
        pyperclip.copy(passcode)  # copy passcode to clipboard
        RightMouseClick()
        time.sleep(self.delay)
        self.wsh.SendKeys("^v")  # CTRL+V
        time.sleep(self.delay)
        self.wsh.SendKeys("{ENTER}")  # press ENTER
        time.sleep(self.delay)

        if self.correct_passcode():
            logging.info(f"Passcode found: {passcode}")
            if len(self.last_codes) > 0:
                logging.info(
                    f'If it is incorrect try the previous attempts: [{", ".join(self.last_codes)}]'
                )
            self.stop()
        else:
            self.tries += 1

    def stop(self) -> None:
        self.stopped = True

    def correct_passcode(self) -> bool:
        image = ImageGrab.grab(
            bbox=(
                self.grey_submit_left,
                self.grey_submit_top,
                self.grey_submit_left + 1,
                self.grey_submit_top + 1,
            )
        )
        return (96, 96, 96) != image.getpixel((0, 0))

    def check_stopped(self) -> bool:
        if self.args.limit and self.tries >= self.args.limit:
            logging.info(
                f"Max tries reached ({str(self.args.limit)}). Stopping..."
            )
            self.watcher.shutdown()
            return True
        if (
            self.args.timeout
            and time.time() - self.start_time >= self.args.timeout
        ):
            logging.info(f"Timeout ({str(self.args.timeout)}s). Stopping...")
            self.watcher.shutdown()
            return True
        if self.stopped:
            return True
        return False


def get_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit", default=None, help="Maximum number of tries", type=int
    )
    parser.add_argument(
        "--timeout",
        default=None,
        help="Maximum time (in seconds) allowed to the script to run",
        type=int,
    )
    parser.add_argument(
        "--brute",
        default=False,
        help="Brute-force attack (default method)",
        action="store_true",
    )
    parser.add_argument(
        "--resumedict",
        default=0,
        help="Line number to resume the dictionary attack",
        type=int,
    )
    parser.add_argument(
        "--min", default=1, help="Minimum length (default = 1)", type=int
    )
    parser.add_argument(
        "--max", default=20, help="Maximum length (default = 20)", type=int
    )
    parser.add_argument(
        "--digits", default=False, help="Include digits", action="store_true"
    )
    parser.add_argument(
        "--lower",
        default=False,
        help="Include lowercase characters",
        action="store_true",
    )
    parser.add_argument(
        "--upper",
        default=False,
        help="Include uppercase characters",
        action="store_true",
    )
    parser.add_argument(
        "--lowercyrillic",
        default=False,
        help="Include lowercase cyrillic characters",
        action="store_true",
    )
    parser.add_argument(
        "--uppercyrillic",
        default=False,
        help="Include uppercase cyrillic characters",
        action="store_true",
    )
    parser.add_argument(
        "--special",
        default=False,
        help="Include special characters",
        action="store_true",
    )
    parser.add_argument(
        "--delay",
        default=35,
        help="Delay in ms between each mouse/keyboard action (default = 50)",
        type=int,
    )
    parser.add_argument(
        "--dict", default=False, help="Dictionary attack", action="store_true"
    )
    parser.add_argument(
        "--dictpath",
        default="./dictionaries/top1000000.txt",
        help="Dictionary file path",
        type=str,
    )

    return parser


def main() -> None:
    parser = get_argument_parser()
    args = parser.parse_args()

    crack_passcode = CrackPasscode(args)
    logging.info("Process started.")
    crack_passcode.start()
    logging.info("Process terminated.")


if __name__ == "__main__":
    main()
