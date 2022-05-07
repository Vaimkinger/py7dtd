#!/usr/bin/env python3

import argparse
import logging
import string
import time
from itertools import product

import win32com.client as comclt
import win32gui
from py7dtd.io.commands_controller import MoveMouseAbsolute, RightMouseClick
from py7dtd.io.key_watcher import KeyWatcher

logging.getLogger(__name__)
logging.root.setLevel(logging.INFO)


class CrackPasscode(object):
    def __init__(self, args):
        self.stopped = False
        self.args = args
        self.init_args()

    def init_args(self):
        if self.args.brute and self.args.dict:
            logging.error(
                "Error: only one method can be selected. Available are: `brute`, `dict`."
            )
            exit()

        if self.args.dict and not self.args.dictpath:
            logging.error("Error: a dictionary must be selected.")
            exit()

        if not self.args.brute and not self.args.dict:
            logging.warning(
                "Warning: a method has not been selected. Available are: `brute`, `dict`.\n`brute` has been selected by default."
            )
            self.args.brute = True

        self.delay = self.args.delay / 1000

    def select_window(self):
        self.wsh = comclt.Dispatch("WScript.Shell")
        self.wsh.AppActivate("7 Days To Die")
        hwnd = win32gui.FindWindow(None, r"7 Days to Die")
        win32gui.SetForegroundWindow(hwnd)
        self.dimensions = win32gui.GetWindowRect(hwnd)

    def center_mouse(self):
        pointer_center = [
            (self.dimensions[2] - self.dimensions[0]) // 2 + self.dimensions[0],
            (self.dimensions[3] - self.dimensions[1]) // 2 + self.dimensions[1] + 20,
        ]
        MoveMouseAbsolute(pointer_center[0], pointer_center[1])

    def start(self):
        self.key_watcher = KeyWatcher(stop_func=self.stop)
        self.key_watcher.start()

        self.tries = 0
        self.start_time = time.time()

        if self.args.brute:
            self.crack_brute()

        if self.args.dict:
            self.crack_dict()

        logging.info("Crack passcode stopped")

    def crack_brute(self):
        allowed_chars = []
        if self.args.digits:
            allowed_chars += string.digits
        if self.args.lower:
            allowed_chars += string.ascii_lowercase
        if self.args.upper:
            allowed_chars += string.ascii_uppercase
        if self.args.special:
            allowed_chars += string.punctuation
            # FIXME: the following characters can not be sent
            allowed_chars.remove("(")
            allowed_chars.remove(")")
            allowed_chars.remove("{")
            allowed_chars.remove("}")
            allowed_chars.remove("~")

        if allowed_chars.count == 0:
            logging.error(
                "Error: empty characters set. Please specify at least one of [digits, lower, upper, special]"
            )
            return

        for length in range(self.args.min, self.args.max + 1):
            to_attempt = product(allowed_chars, repeat=length)

            for attempt in to_attempt:
                self.inject_string("".join(attempt))
                self.tries += 1
                if self.check_stopped():
                    return

    def crack_dict(self):
        with open(self.args.dictpath, "r") as dict_file:
            for line in dict_file:
                self.inject_string(line.strip())
                self.tries += 1
                if self.check_stopped():
                    return

    def inject_string(self, attempt):
        time.sleep(self.delay)
        RightMouseClick()
        time.sleep(self.delay)
        self.wsh.SendKeys(attempt)
        time.sleep(self.delay)
        self.wsh.SendKeys("~")
        time.sleep(self.delay)

    def stop(self):
        self.stopped = True

    def check_stopped(self):
        if self.args.limit and self.tries >= self.args.limit:
            logging.info(
                "Max tries reached (" + str(self.args.limit) + "). Stopping..."
            )
            self.key_watcher.shutdown()
            return True
        if self.args.timeout and time.time() - self.start_time >= self.args.timeout:
            logging.info("Timeout (" + str(self.args.timeout) + "s). Stopping...")
            self.key_watcher.shutdown()
            return True
        if self.stopped:
            return True

def get_argument_parser():
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
        help="Bruteforce attack (default method)",
        action="store_true",
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
        "--special",
        default=False,
        help="Include special characters",
        action="store_true",
    )
    parser.add_argument(
        "--delay",
        default=50,
        help="Delay in ms between each mouse/keyboard action (default = 50)",
        type=int,
    )
    parser.add_argument(
        "--dict", default=False, help="Dictionary attack", action="store_true"
    )
    parser.add_argument("--dictpath", help="Dictionary file path", type=str)

    return parser

def main():
    parser = get_argument_parser()
    args = parser.parse_args()

    crack_passcode = CrackPasscode(args)
    crack_passcode.select_window()
    crack_passcode.center_mouse()
    crack_passcode.start()

if __name__ == "__main__":
    main()
