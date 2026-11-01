#!/usr/bin/env python3
"""One-time private setup in the user's own POSIX Terminal; never calls an API."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import stat
import sys
import warnings


class SetupError(Exception):
    def __init__(self, code):
        self.code = code


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise SetupError("invalid_arguments")


def same(first, second):
    return first.st_dev == second.st_dev and first.st_ino == second.st_ino


def owned_directory(path, uid, private):
    info = path.lstat()
    mask = 0o077 if private else 0o022
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & mask:
        raise SetupError("unsafe_directory")
    return info


def ensure_directory(path, uid, private):
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    return owned_directory(path, uid, private)


def project_guard(path, home):
    # The fixed config location is not a selected project. Refuse recognized
    # Git worktrees and a non-home current directory containing that location.
    cwd = Path.cwd().resolve()
    if cwd != home and cwd != Path(cwd.anchor) and (path == cwd or cwd in path.parents):
        raise SetupError("project_path_refused")
    for directory in path.parents:
        try:
            (directory / ".git").lstat()
        except FileNotFoundError:
            continue
        raise SetupError("project_path_refused")


def verify_directories(snapshots, uid):
    for path, original, private in snapshots:
        current = owned_directory(path, uid, private)
        if not same(original, current) or original.st_mode != current.st_mode or os.path.realpath(path) != str(path):
            raise SetupError("directory_changed")


def run(argv=None):
    Parser(description="Create ~/.config/flamingo-api/rapidapi.key privately. Run in your own Terminal; no API calls, overwrite or rotation.").parse_args(argv)
    if os.name != "posix":
        raise SetupError("posix_required")
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise SetupError("terminal_required")
    uid = os.geteuid()
    home = Path(os.path.realpath(Path.home()))
    home_info = owned_directory(home, uid, False)
    config = home / ".config"
    directory = config / "flamingo-api"
    target = directory / "rapidapi.key"
    project_guard(target, home)
    config_info = ensure_directory(config, uid, False)
    directory_info = ensure_directory(directory, uid, True)
    snapshots = ((home, home_info, False), (config, config_info, False), (directory, directory_info, True))
    try:
        target.lstat()
    except FileNotFoundError:
        pass
    else:
        raise SetupError("key_file_exists")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("RapidAPI application key (hidden; no API call): ", stream=sys.stderr)
        except getpass.GetPassWarning:
            raise SetupError("secure_terminal_unavailable") from None
    if not re.fullmatch(r"[\x21-\x7e]{16,512}", key):
        raise SetupError("invalid_key")
    if key in str(target):
        raise SetupError("invalid_key")
    data = key.encode("ascii") + b"\n"
    # Revalidate the directories after the private prompt, before creation.
    verify_directories(snapshots, uid)
    fd, created = None, None
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        created = os.fstat(fd)
        os.fchmod(fd, 0o600)
        if not stat.S_ISREG(created.st_mode) or created.st_uid != uid:
            raise SetupError("unsafe_key_file")
        verify_directories(snapshots, uid)
        if not same(created, target.lstat()):
            raise SetupError("unsafe_key_file")
        offset = 0
        while offset < len(data):
            written = os.write(fd, data[offset:])
            if written <= 0:
                raise SetupError("write_failed")
            offset += written
        os.fsync(fd)
        after, named = os.fstat(fd), target.lstat()
        if (not same(after, named) or not stat.S_ISREG(named.st_mode) or after.st_uid != uid or
            stat.S_IMODE(after.st_mode) != 0o600 or after.st_size != len(data)):
            raise SetupError("unsafe_key_file")
        verify_directories(snapshots, uid)
    except BaseException:
        if created is not None:
            try:
                named = target.lstat()
                if stat.S_ISREG(named.st_mode) and same(created, named):
                    target.unlink()
            except OSError:
                pass
        raise
    finally:
        if fd is not None:
            os.close(fd)
    return {"ok": True, "status": "created", "key_file": str(target), "subscription_verified": False}


def main():
    try:
        result = run()
    except SetupError as error:
        result = {"ok": False, "status": error.code}
    except FileExistsError:
        result = {"ok": False, "status": "key_file_exists"}
    except (EOFError, KeyboardInterrupt):
        result = {"ok": False, "status": "cancelled"}
    except Exception:
        result = {"ok": False, "status": "setup_failed"}
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
