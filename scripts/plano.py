#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from __future__ import print_function

import atexit as _atexit
import base64 as _base64
import binascii as _binascii
import codecs as _codecs
import collections as _collections
import ctypes as _ctypes
import fnmatch as _fnmatch
import getpass as _getpass
import json as _json
import os as _os
import random as _random
import re as _re
import shlex as _shlex
import shutil as _shutil
import signal as _signal
import socket as _socket
import subprocess as _subprocess
import sys as _sys
import tarfile as _tarfile
import tempfile as _tempfile
import time as _time
import traceback as _traceback
import types as _types
import uuid as _uuid

LINE_SEP = _os.linesep
PATH_SEP = _os.sep
PATH_VAR_SEP = _os.pathsep
ENV = _os.environ
ARGS = _sys.argv

STDIN = _sys.stdin
STDOUT = _sys.stdout
STDERR = _sys.stderr
DEVNULL = _os.devnull

_message_levels = (
    "debug",
    "notice",
    "warn",
    "error",
)

_debug = _message_levels.index("debug")
_notice = _message_levels.index("notice")
_warn = _message_levels.index("warn")
_error = _message_levels.index("error")

_message_output = STDERR
_message_threshold = _notice

def enable_logging(level=None, output=None):
    if level is not None:
        if level == "warning":
            level = "warn"

        assert level in _message_levels

        global _message_threshold
        _message_threshold = _message_levels.index(level)

    if output is not None:
        if _is_string(output):
            output = open(output, "w")

        global _message_output
        _message_output = output

def disable_logging():
    global _message_threshold
    _message_threshold = 4

def fail(message, *args):
    error(message, *args)

    if isinstance(message, BaseException):
        raise message

    raise PlanoException(message.format(*args))

def error(message, *args):
    _print_message("Error", message, args)

def warn(message, *args):
    if _message_threshold <= _warn:
        _print_message("Warning", message, args)

def notice(message, *args):
    if _message_threshold <= _notice:
        _print_message(None, message, args)

def debug(message, *args):
    if _message_threshold <= _debug:
        _print_message("Debug", message, args)

def exit(arg=None, *args):
    if arg in (0, None):
        _sys.exit()

    if _is_string(arg):
        error(arg, args)
        _sys.exit(1)

    if isinstance(arg, int):
        if arg > 0:
            error("Exiting with code {0}", arg)
        else:
            notice("Exiting with code {0}", arg)

        _sys.exit(arg)

    raise Exception()

def _print_message(category, message, args):
    if _message_output is None:
        return

    message = _format_message(category, message, args)

    print(message, file=_message_output)

    _message_output.flush()

def _format_message(category, message, args):
    if not _is_string(message):
        message = str(message)

    if args:
        message = message.format(*args)

    if len(message) > 0 and message[0].islower():
        message = message[0].upper() + message[1:]

    if category:
        message = "{0}: {1}".format(category, message)

    program = get_program_name()
    message = "{0}: {1}".format(program, message)

    return message

def eprint(*args, **kwargs):
    print(*args, file=_sys.stderr, **kwargs)

def flush():
    STDOUT.flush()
    STDERR.flush()

get_absolute_path = _os.path.abspath
normalize_path = _os.path.normpath
get_real_path = _os.path.realpath
exists = _os.path.lexists
is_absolute = _os.path.isabs
is_dir = _os.path.isdir
is_file = _os.path.isfile
is_link = _os.path.islink
get_file_size = _os.path.getsize

join = _os.path.join
split = _os.path.split
split_extension = _os.path.splitext

get_current_dir = _os.getcwd

def get_home_dir(user=None):
    return _os.path.expanduser("~{0}".format(user or ""))

def get_user():
    return _getpass.getuser()

def get_hostname():
    return _socket.gethostname()

def get_parent_dir(path):
    path = normalize_path(path)
    parent, child = split(path)

    return parent

def get_file_name(file_):
    file_ = normalize_path(file_)
    dir_, name = split(file_)

    return name

def get_name_stem(file_):
    name = get_file_name(file_)

    if name.endswith(".tar.gz"):
        name = name[:-3]

    stem, ext = split_extension(name)

    return stem

def get_name_extension(file_):
    name = get_file_name(file_)
    stem, ext = split_extension(name)

    return ext

def get_program_name(command=None):
    if command is None:
        args = ARGS
    else:
        args = command.split()

    for arg in args:
        if "=" not in arg:
            return get_file_name(arg)

def which(program_name):
    assert "PATH" in ENV

    for dir_ in ENV["PATH"].split(PATH_VAR_SEP):
        program = join(dir_, program_name)

        if _os.access(program, _os.X_OK):
            return program

def read(file_):
    with _codecs.open(file_, encoding="utf-8", mode="r") as f:
        return f.read()

def write(file_, string):
    make_parent_dir(file_, quiet=True)

    with _codecs.open(file_, encoding="utf-8", mode="w") as f:
        f.write(string)

    return file_

def append(file_, string):
    make_parent_dir(file_, quiet=True)

    with _codecs.open(file_, encoding="utf-8", mode="a") as f:
        f.write(string)

    return file_

def prepend(file_, string):
    orig = read(file_)
    return write(file_, string + orig)

def touch(file_):
    try:
        _os.utime(file_, None)
    except OSError:
        append(file_, "")

    return file_

def tail(file_, n):
    return "".join(tail_lines(file_, n))

def read_lines(file_):
    with _codecs.open(file_, encoding="utf-8", mode="r") as f:
        return f.readlines()

def write_lines(file_, lines):
    make_parent_dir(file_, quiet=True)

    with _codecs.open(file_, encoding="utf-8", mode="r") as f:
        f.writelines(lines)

    return file_

def append_lines(file_, lines):
    make_parent_dir(file_, quiet=True)

    with _codecs.open(file_, encoding="utf-8", mode="a") as f:
        f.writelines(string)

    return file_

def prepend_lines(file_, lines):
    orig_lines = read_lines(file_)

    make_parent_dir(file_, quiet=True)

    with _codecs.open(file_, encoding="utf-8", mode="w") as f:
        f.writelines(lines)
        f.writelines(orig_lines)

    return file_

# Derived from http://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
def tail_lines(file_, n):
    assert n >= 0

    with _codecs.open(file_, encoding="utf-8", mode="r") as f:
        pos = n + 1
        lines = list()

        while len(lines) <= n:
                try:
                    f.seek(-pos, 2)
                except IOError:
                    f.seek(0)
                    break
                finally:
                    lines = f.readlines()

                pos *= 2

        return lines[-n:]

def read_json(file_):
    with _codecs.open(file_, encoding="utf-8", mode="r") as f:
        return _json.load(f)

def write_json(file_, obj):
    make_parent_dir(file_, quiet=True)

    with _codecs.open(file_, encoding="utf-8", mode="w") as f:
        return _json.dump(obj, f, indent=4, separators=(",", ": "), sort_keys=True)

def parse_json(json):
    return _json.loads(json)

def emit_json(obj):
    return _json.dumps(obj, f, indent=4, separators=(",", ": "), sort_keys=True)

def http_get(url, output_file=None, insecure=False):
    options = [
        "-sf",
        "-H", "'Expect:'",
    ]

    if insecure:
        options.append("--insecure")

    if output_file is None:
        return call_for_stdout("curl {0} {1}", " ".join(options), url)

    call("curl {0} {1} -o {2}", " ".join(options), url, output_file)

def http_put(url, input_file, output_file=None, insecure=False):
    options = [
        "-sf",
        "-X", "PUT",
        "-H", "'Expect:'",
    ]

    if insecure:
        options.append("--insecure")

    if output_file is None:
        return call_for_stdout("curl {0} {1} -d @{2}", " ".join(options), url, input_file)

    call("curl {0} {1} -d @{2} -o {3}", " ".join(options), url, input_file, output_file)

def http_get_json(url, insecure=False):
    return parse_json(http_get(url, insecure=insecure))

def http_put_json(url, data, insecure=False):
    with temp_file() as f:
        write_json(f, data)
        http_put(url, f, insecure=insecure)

def get_temp_dir():
    return _tempfile.gettempdir()

def get_user_temp_dir():
    try:
        return ENV["XDG_RUNTIME_DIR"]
    except KeyError:
        return join(get_temp_dir(), get_user())

def make_temp_file(suffix="", dir=None):
    if dir is None:
        dir = get_temp_dir()

    return _tempfile.mkstemp(prefix="plano-", suffix=suffix, dir=dir)[1]

def make_temp_dir(suffix="", dir=None):
    if dir is None:
        dir = get_temp_dir()

    return _tempfile.mkdtemp(prefix="plano-", suffix=suffix, dir=dir)

class temp_file(object):
    def __init__(self, suffix="", dir=None):
        self._file = make_temp_file(suffix=suffix, dir=dir)

    def __enter__(self):
        return self._file

    def __exit__(self, exc_type, exc_value, traceback):
        remove(self._file, quiet=True)

# No args constructor gets a temp dir
class working_dir(object):
    def __init__(self, dir_=None, remove=False):
        self._dir = dir_
        self._prev_dir = None
        self._remove = remove

        if self._dir is None:
            self._dir = make_temp_dir()
            self._remove = True

    def __enter__(self):
        make_dir(self._dir, quiet=True)

        notice("Entering directory '{0}'", get_absolute_path(self._dir))

        self._prev_dir = change_dir(self._dir, quiet=True)

        return self._dir

    def __exit__(self, exc_type, exc_value, traceback):
        if self._dir is None or self._dir == ".":
            return

        notice("Returning to directory '{0}'", get_absolute_path(self._prev_dir))

        change_dir(self._prev_dir, quiet=True)

        if self._remove:
            remove(self._dir, quiet=True)

# Length in bytes, renders twice as long in hex
def get_unique_id(length=16):
    assert length >= 1
    assert length <= 16

    uuid_bytes = _uuid.uuid4().bytes
    uuid_bytes = uuid_bytes[:length]

    return _binascii.hexlify(uuid_bytes).decode("utf-8")

def base64_encode(string):
    return _base64.b64encode(string)

def base64_decode(string):
    return _base64.b64decode(string)

def copy(from_path, to_path, quiet=False):
    if not quiet:
        notice("Copying '{0}' to '{1}'", from_path, to_path)

    if is_dir(to_path):
        to_path = join(to_path, get_file_name(from_path))
    else:
        make_parent_dir(to_path, quiet=True)

    if is_dir(from_path):
        _copytree(from_path, to_path, symlinks=True)
    else:
        _shutil.copy(from_path, to_path)

    return to_path

def move(from_path, to_path, quiet=False):
    if not quiet:
        notice("Moving '{0}' to '{1}'", from_path, to_path)

    if is_dir(to_path):
        to_path = join(to_path, get_file_name(from_path))
    else:
        make_parent_dir(to_path, quiet=True)

    _shutil.move(from_path, to_path)

    return to_path

def rename(path, expr, replacement):
    path = normalize_path(path)
    parent_dir, name = split(path)
    to_name = string_replace(name, expr, replacement)
    to_path = join(parent_dir, to_name)

    notice("Renaming '{0}' to '{1}'", path, to_path)

    move(path, to_path)

    return to_path

def remove(path, quiet=False):
    if not quiet:
        notice("Removing '{0}'", path)

    if not exists(path):
        return

    if is_dir(path):
        _shutil.rmtree(path, ignore_errors=True)
    else:
        _os.remove(path)

    return path

def make_link(source_path, link_file):
    notice("Making link '{0}' to '{1}'", link_file, source_path)

    if exists(link_file):
        assert read_link(link_file) == source_path
        return

    link_dir = get_parent_dir(link_file)

    if link_dir:
        make_dir(link_dir)

    _os.symlink(source_path, link_file)

    return link_file

def read_link(file):
    return _os.readlink(file)

def find(dir, *patterns):
    matched_paths = set()

    if not patterns:
        patterns = ("*",)

    for root, dirs, files in _os.walk(dir):
        for pattern in patterns:
            matched_dirs = _fnmatch.filter(dirs, pattern)
            matched_files = _fnmatch.filter(files, pattern)

            matched_paths.update([join(root, x) for x in matched_dirs])
            matched_paths.update([join(root, x) for x in matched_files])

    return sorted(matched_paths)

def find_any_one(dir, *patterns):
    paths = find(dir, *patterns)

    if len(paths) == 0:
        return

    return paths[0]

def find_only_one(dir, *patterns):
    paths = find(dir, *patterns)

    if len(paths) == 0:
        return

    if len(paths) > 1:
        fail("Found multiple files: {0}", ", ".join(paths))

    assert len(paths) == 1

    return paths[0]

def find_exactly_one(dir, *patterns):
    path = find_only_one(dir, *patterns)

    if path is None:
        fail("Found no matching files")

    return path

def configure_file(input_file, output_file, **substitutions):
    notice("Configuring '{0}' for output '{1}'", input_file, output_file)

    content = read(input_file)

    for name, value in substitutions.items():
        content = content.replace("@{0}@".format(name), value)

    write(output_file, content)

    _shutil.copymode(input_file, output_file)

def make_dir(dir_, quiet=False):
    if not quiet:
        notice("Making directory '{0}'", dir_)

    if dir_ == "":
        return dir_

    if not exists(dir_):
        _os.makedirs(dir_)

    return dir_

def make_parent_dir(path, quiet=False):
    return make_dir(get_parent_dir(path), quiet=quiet)

# Returns the current working directory so you can change it back
def change_dir(dir_, quiet=False):
    if not quiet:
        notice("Changing directory to '{0}'", dir_)

    try:
        cwd = get_current_dir()
    except FileNotFoundError:
        cwd = None

    _os.chdir(dir_)

    return cwd

def list_dir(dir_, *patterns):
    assert is_dir(dir_)

    names = _os.listdir(dir_)

    if not patterns:
        return sorted(names)

    matched_names = set()

    for pattern in patterns:
        matched_names.update(_fnmatch.filter(names, pattern))

    return sorted(matched_names)

class working_env(object):
    def __init__(self, **env_vars):
        self.env_vars = env_vars
        self.prev_env_vars = dict()

    def __enter__(self):
        for name, value in self.env_vars.items():
            if name in ENV:
                self.prev_env_vars[name] = ENV[name]

            ENV[name] = str(value)

    def __exit__(self, exc_type, exc_value, traceback):
        for name, value in self.env_vars.items():
            if name in self.prev_env_vars:
                ENV[name] = self.prev_env_vars[name]
            else:
                del ENV[name]

## Process operations

def get_process_id():
    return _os.getpid()

def sleep(seconds, quiet=False):
    if not quiet:
        notice("Sleeping for {0} {1}", seconds, plural("second", seconds))

    _time.sleep(seconds)

# quiet=False - Don't log at notice level
# stash=False - No output unless there is an error
# output=<file> - Send stdout and stderr to a file
# stdout=<file> - Send stdout to a file
# stderr=<file> - Send stderr to a file
def start(command, *args, **options):
    if options.pop("quiet", False):
        debug("Starting '{0}'", _format_command(command, args, None))
    else:
        notice("Starting '{0}'", _format_command(command, args, None))

    stdout = options.get("stdout", _sys.stdout)
    stderr = options.get("stderr", _sys.stderr)

    if "output" in options:
        out = options.pop("output")
        stdout, stderr = out, out

    if _is_string(stdout):
        stdout = open(stdout, "w")

    if _is_string(stderr):
        stderr = open(stderr, "w")

    options["stdout"] = stdout
    options["stderr"] = stderr

    temp_output_file = None

    if options.pop("stash", False) is True:
        temp_output_file = make_temp_file()
        temp_output = open(temp_output_file, "w")

        options["stdout"] = temp_output
        options["stderr"] = temp_output

    if "preexec_fn" not in options and _libc is not None:
        options["preexec_fn"] = _libc.prctl(1, _signal.SIGKILL)

    try:
        proc = PlanoProcess(command, options, temp_output_file)
    except OSError as e:
        if e.errno == 2:
            fail(e)

        raise

    debug("{0} started", proc)

    return proc

def stop(proc, quiet=False):
    if quiet:
        debug("Stopping {0}", proc)
    else:
        notice("Stopping {0}", proc)

    if proc.poll() is not None:
        if proc.exit_code == 0:
            debug("{0} already exited normally", proc)
        elif proc.exit_code == -(_signal.SIGTERM):
            debug("{0} was already terminated", proc)
        else:
            debug("{0} already exited with code {1}", proc, proc.exit_code)

        return proc

    proc.terminate()

    # XXX kill after timeout

    return wait(proc, quiet=True)

def wait(proc, check=False, quiet=False):
    if quiet:
        debug("Waiting for {0} to exit", proc)
    else:
        notice("Waiting for {0} to exit", proc)

    proc.wait()

    if proc.exit_code == 0:
        debug("{0} exited normally", proc)
    elif proc.exit_code < 0:
        debug("{0} was terminated by signal {1}", proc, abs(proc.exit_code))
    else:
        debug("{0} exited with code {1}", proc, proc.exit_code)

    if proc.temp_output_file is not None:
        if proc.exit_code > 0:
            eprint(read(proc.temp_output_file), end="")

        remove(proc.temp_output_file, quiet=True)

    if check and proc.exit_code > 0:
        raise PlanoProcessError(proc)

    return proc

def run(command, *args, **options):
    if options.get("quiet", False):
        debug("Running '{0}'", _format_command(command, args))
    else:
        notice("Running '{0}'", _format_command(command, args))

    check = options.pop("check", True)
    options["quiet"] = True

    proc = start(command, *args, **options)

    return wait(proc, check=check, quiet=True)

def call(command, *args, **options):
    if options.pop("quiet", False):
        debug("Calling '{0}'", _format_command(command, args))
    else:
        notice("Calling '{0}'", _format_command(command, args))

    if any([x in options for x in ("check", "stash", "output", "stdout", "stderr")]):
        raise PlanoException("Illegal options")

    options["quiet"] = True
    options["stdout"] = _subprocess.PIPE
    options["stderr"] = _subprocess.PIPE

    proc = start(command, *args, **options)
    out, err = proc.communicate()

    if proc.exit_code > 0:
        error = PlanoProcessError(proc)
        error.stdout, error.stderr = out, err
        raise error

    if out is None:
        out = b""

    return out.decode("utf-8")

_child_processes = list()

class PlanoProcess(_subprocess.Popen):
    def __init__(self, command, options, temp_output_file):
        assert _is_string(command), command

        if options.get("shell", False):
            args = command
        else:
            args = _shlex.split(command)

        super(PlanoProcess, self).__init__(args, **options)

        self.command = command
        self.temp_output_file = temp_output_file

        _child_processes.append(self)

    @property
    def exit_code(self):
        return self.returncode

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.stdout:
            self.stdout.close()
        if self.stderr:
            self.stderr.close()
        try:
            if self.stdin:
                self.stdin.close()
        finally:
            stop(self)

    def __repr__(self):
        return "process {0} ('{1}')".format(self.pid, _format_command(self.command, None, 40))

class PlanoException(Exception):
    pass

class PlanoProcessError(_subprocess.CalledProcessError, PlanoException):
    def __init__(self, proc):
        super(PlanoProcessError, self).__init__(proc.exit_code, proc.command)

def default_sigterm_handler(signum, frame):
    for proc in _child_processes:
        if proc.poll() is None:
            proc.terminate()

    exit(-(_signal.SIGTERM))

_signal.signal(_signal.SIGTERM, default_sigterm_handler)

def _format_command(command, args, max=None):
    if args:
        command = command.format(*args)

    return shorten(command.replace("\n", "\\n"), max, ellipsis="...")

_libc = None

if _sys.platform == "linux2":
    try:
        _libc = _ctypes.CDLL(_ctypes.util.find_library("c"))
    except:
        _traceback.print_exc()

def make_archive(input_dir, output_dir, archive_stem):
    assert is_dir(input_dir), input_dir
    assert is_dir(output_dir), output_dir
    assert _is_string(archive_stem), archive_stem

    with temp_working_dir() as dir_:
        temp_input_dir = join(dir_, archive_stem)

        copy(input_dir, temp_input_dir)
        make_dir(output_dir)

        output_file = "{0}.tar.gz".format(join(output_dir, archive_stem))
        output_file = get_absolute_path(output_file)

        call("tar -czf {0} {1}", output_file, archive_stem)

    return output_file

def extract_archive(archive_file, output_dir=None):
    assert is_file(archive_file), archive_file
    assert output_dir is None or is_dir(output_dir), output_dir

    archive_file = get_absolute_path(archive_file)

    with working_dir(output_dir):
        call("tar -xf {0}", archive_file)

    return output_dir

def rename_archive(archive_file, new_archive_stem):
    assert is_file(archive_file), archive_file
    assert _is_string(new_archive_stem), new_archive_stem

    if name_stem(archive_file) == new_archive_stem:
        return archive_file

    with temp_working_dir() as dir_:
        extract_archive(archive_file, dir_)

        input_name = list_dir(dir_)[0]
        input_dir = join(dir_, input_name)
        output_file = make_archive(input_dir, dir_, new_archive_stem)
        output_name = get_file_name(output_file)
        archive_dir = get_parent_dir(archive_file)
        new_archive_file = join(archive_dir, output_name)

        move(output_file, new_archive_file)
        remove(archive_file)

    return new_archive_file

def get_random_port(min=49152, max=65535):
    return _random.randint(min, max)

def wait_for_port(port, host="", timeout=30):
    if _is_string(port):
        port = int(port)

    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)

    start = _time.time()

    try:
        while True:
            if sock.connect_ex((host, port)) == 0:
                return

            sleep(0.1, quiet=True)

            if _time.time() - start > timeout:
                fail("Timed out waiting for port {0} to open", port)
    finally:
        sock.close()

def string_replace(string, expr, replacement, count=0):
    return _re.sub(expr, replacement, string, count)

def nvl(value, substitution, template=None):
    assert substitution is not None

    if value is None:
        return substitution

    if template is not None:
        return template.format(value)

    return value

def shorten(string, max_, ellipsis=""):
    assert max_ is None or isinstance(max_, int)

    if string is None:
        return ""

    if max_ is None or len(string) < max_:
        return string
    else:
        if ellipsis:
            string = string + ellipsis
            end = max(0, max_ - len(ellipsis))
            return string[0:end] + ellipsis
        else:
            return string[0:max_]

def plural(noun, count=0):
    if noun in (None, ""):
        return ""

    if count == 1:
        return noun

    if noun.endswith("s"):
        return "{0}ses".format(noun)

    return "{0}s".format(noun)

# Modified copytree impl that allows for already existing destination
# dirs
def _copytree(src, dst, symlinks=False, ignore=None):
    """Recursively copy a directory tree using copy2().

    If exception(s) occur, an Error is raised with a list of reasons.

    If the optional symlinks flag is true, symbolic links in the
    source tree result in symbolic links in the destination tree; if
    it is false, the contents of the files pointed to by symbolic
    links are copied.

    The optional ignore argument is a callable. If given, it
    is called with the `src` parameter, which is the directory
    being visited by copytree(), and `names` which is the list of
    `src` contents, as returned by os.listdir():

        callable(src, names) -> ignored_names

    Since copytree() is called recursively, the callable will be
    called once for each directory that is copied. It returns a
    list of names relative to the `src` directory that should
    not be copied.

    XXX Consider this example code rather than the ultimate tool.

    """
    names = _os.listdir(src)
    if ignore is not None:
        ignored_names = ignore(src, names)
    else:
        ignored_names = set()

    if not exists(dst):
        _os.makedirs(dst)
    errors = []
    for name in names:
        if name in ignored_names:
            continue
        srcname = _os.path.join(src, name)
        dstname = _os.path.join(dst, name)
        try:
            if symlinks and _os.path.islink(srcname):
                linkto = _os.readlink(srcname)
                _os.symlink(linkto, dstname)
            elif _os.path.isdir(srcname):
                _copytree(srcname, dstname, symlinks, ignore)
            else:
                # Will raise a SpecialFileError for unsupported file types
                _shutil.copy2(srcname, dstname)
        # catch the Error from the recursive copytree so that we can
        # continue with other files
        except _shutil.Error as err:
            errors.extend(err.args[0])
        except EnvironmentError as why:
            errors.append((srcname, dstname, str(why)))
    try:
        _shutil.copystat(src, dst)
    except OSError as why:
        if _shutil.WindowsError is not None and isinstance \
               (why, _shutil.WindowsError):
            # Copying file access times may fail on Windows
            pass
        else:
            errors.append((src, dst, str(why)))
    if errors:
        raise _shutil.Error(errors)

def _is_string(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)
