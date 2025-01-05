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

import base64 as _base64
import binascii as _binascii
import code as _code
import datetime as _datetime
import fnmatch as _fnmatch
import getpass as _getpass
import json as _json
import os as _os
import pprint as _pprint
import pkgutil as _pkgutil
import random as _random
import re as _re
import shlex as _shlex
import shutil as _shutil
import signal as _signal
import socket as _socket
import subprocess as _subprocess
import sys as _sys
import tempfile as _tempfile
import time as _time
import traceback as _traceback
import urllib as _urllib
import urllib.parse as _urllib_parse
import uuid as _uuid

_max = max

## Exceptions

class PlanoException(Exception):
    pass

class PlanoError(PlanoException):
    pass

class PlanoTimeout(PlanoException):
    pass

## Global variables

ENV = _os.environ
ARGS = _sys.argv

STDIN = _sys.stdin
STDOUT = _sys.stdout
STDERR = _sys.stderr
DEVNULL = _os.devnull

LINUX = _sys.platform == "linux"
WINDOWS = _sys.platform in ("win32", "cygwin")

PLANO_DEBUG = "PLANO_DEBUG" in ENV
PLANO_COLOR = "PLANO_COLOR" in ENV

## Archive operations

def make_archive(input_dir, output_file=None, quiet=False):
    check_program("tar")

    archive_stem = get_base_name(input_dir)

    if output_file is None:
        # tar on Windows needs this
        base = join(get_current_dir(), archive_stem)
        base = base.replace("\\", "/")

        output_file = f"{base}.tar.gz"

    _notice(quiet, "Making archive {} from directory {}", repr(output_file), repr(input_dir))

    with working_dir(get_parent_dir(input_dir), quiet=True):
        run(f"tar -czf {output_file} {archive_stem}", quiet=True)

    return output_file

def extract_archive(input_file, output_dir=None, quiet=False):
    check_program("tar")

    if output_dir is None:
        output_dir = get_current_dir()

    _notice(quiet, "Extracting archive {} to directory {}", repr(input_file), repr(output_dir))

    input_file = get_absolute_path(input_file)

    # tar on Windows needs this
    input_file = input_file.replace("\\", "/")

    with working_dir(output_dir, quiet=True):
        run(f"tar -xf {input_file}", quiet=True)

    return output_dir

def rename_archive(input_file, new_archive_stem, quiet=False):
    _notice(quiet, "Renaming archive {} with stem {}", repr(input_file), repr(new_archive_stem))

    output_dir = get_absolute_path(get_parent_dir(input_file))
    output_file = "{}.tar.gz".format(join(output_dir, new_archive_stem))

    # tar on Windows needs this
    output_file = output_file.replace("\\", "/")

    input_file = get_absolute_path(input_file)

    with working_dir(quiet=True):
        extract_archive(input_file, quiet=True)

        input_name = list_dir()[0]
        input_dir = move(input_name, new_archive_stem, quiet=True)

        make_archive(input_dir, output_file=output_file, quiet=True)

    remove(input_file, quiet=True)

    return output_file

## Console operations

def flush():
    _sys.stdout.flush()
    _sys.stderr.flush()

def eprint(*args, **kwargs):
    print(*args, file=_sys.stderr, **kwargs)

def pprint(*args, **kwargs):
    args = [pformat(x) for x in args]
    print(*args, **kwargs)

_color_codes = {
    "black": "\u001b[30",
    "red": "\u001b[31",
    "green": "\u001b[32",
    "yellow": "\u001b[33",
    "blue": "\u001b[34",
    "magenta": "\u001b[35",
    "cyan": "\u001b[36",
    "white": "\u001b[37",
    "gray": "\u001b[90",
}

_color_reset = "\u001b[0m"

def _get_color_code(color, bright):
    elems = [_color_codes[color]]

    if bright:
        elems.append(";1")

    elems.append("m")

    return "".join(elems)

def _is_color_enabled(file):
    return PLANO_COLOR or hasattr(file, "isatty") and file.isatty()

class console_color:
    def __init__(self, color=None, bright=False, file=_sys.stdout):
        self.file = file
        self.color_code = None

        if (color, bright) != (None, False):
            self.color_code = _get_color_code(color, bright)

        self.enabled = self.color_code is not None and _is_color_enabled(self.file)

    def __enter__(self):
        if self.enabled:
            print(self.color_code, file=self.file, end="", flush=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.enabled:
            print(_color_reset, file=self.file, end="", flush=True)

def cformat(value, color=None, bright=False, file=_sys.stdout):
    if (color, bright) != (None, False) and _is_color_enabled(file):
        return "".join((_get_color_code(color, bright), value, _color_reset))
    else:
        return value

def cprint(*args, **kwargs):
    color = kwargs.pop("color", "white")
    bright = kwargs.pop("bright", False)
    file = kwargs.get("file", _sys.stdout)

    with console_color(color, bright=bright, file=file):
        print(*args, **kwargs)

class output_redirected:
    def __init__(self, output, quiet=False):
        self.output = output
        self.quiet = quiet

    def __enter__(self):
        flush()

        _notice(self.quiet, "Redirecting output to file {}", repr(self.output))

        if is_string(self.output):
            output = open(self.output, "w")

        self.prev_stdout, self.prev_stderr = _sys.stdout, _sys.stderr
        _sys.stdout, _sys.stderr = output, output

    def __exit__(self, exc_type, exc_value, traceback):
        flush()

        _sys.stdout, _sys.stderr = self.prev_stdout, self.prev_stderr

try:
    breakpoint
except NameError: # pragma: nocover
    def breakpoint():
        import pdb
        pdb.set_trace()

def repl(locals): # pragma: nocover
    _code.InteractiveConsole(locals=locals).interact()

def print_properties(props, file=None):
    size = max([len(x[0]) for x in props])

    for prop in props:
        name = "{}:".format(prop[0])
        template = "{{:<{}}}  ".format(size + 1)

        print(template.format(name), prop[1], end="", file=file)

        for value in prop[2:]:
            print(" {}".format(value), end="", file=file)

        print(file=file)

## Directory operations

def find(dirs=None, include="*", exclude=[]):
    if dirs is None:
        dirs = "."

    if is_string(dirs):
        dirs = [dirs]

    if is_string(include):
        include = [include]

    if is_string(exclude):
        exclude = [exclude]

    found = set()

    for dir in dirs:
        for root, dir_names, file_names in _os.walk(dir, followlinks=True):
            names = dir_names + file_names

            for include_pattern in include:
                names = _fnmatch.filter(names, include_pattern)

                for exclude_pattern in exclude:
                    for name in _fnmatch.filter(names, exclude_pattern):
                        names.remove(name)

                root = root.removeprefix("./")

                if root == ".":
                    root = ""

                found.update([join(root, x) for x in names])

    return sorted(found)

def make_dir(dir, quiet=False):
    if dir == "":
        return dir

    if not exists(dir):
        _notice(quiet, "Making directory '{}'", dir)
        _os.makedirs(dir)

    return dir

def make_parent_dir(path, quiet=False):
    return make_dir(get_parent_dir(path), quiet=quiet)

# Returns the current working directory so you can change it back
def change_dir(dir, quiet=False):
    _debug(quiet, "Changing directory to {}", repr(dir))

    prev_dir = get_current_dir()

    if not dir:
        return prev_dir

    _os.chdir(dir)

    return prev_dir

def list_dir(dir=None, include="*", exclude=[]):
    if dir is None:
        dir = get_current_dir()
    else:
        dir = expand(dir)

    assert is_dir(dir), dir

    if is_string(include):
        include = [include]

    if is_string(exclude):
        exclude = [exclude]

    names = _os.listdir(dir)

    for include_pattern in include:
        names = _fnmatch.filter(names, include_pattern)

        for exclude_pattern in exclude:
            for name in _fnmatch.filter(names, exclude_pattern):
                names.remove(name)

    return sorted(names)

def print_dir(dir=None, include="*", exclude=[]):
    if dir is None:
        dir = get_current_dir()
    else:
        dir = expand(dir)

    names = list_dir(dir=dir, include=include, exclude=exclude)

    print("{}:".format(get_absolute_path(dir)))

    if names:
        for name in names:
            print(f"  {name}")
    else:
        print("  [none]")

# No args constructor gets a temp dir
class working_dir:
    def __init__(self, dir=None, quiet=False):
        self.dir = dir
        self.prev_dir = None
        self.remove = False
        self.quiet = quiet

        if self.dir is None:
            self.dir = make_temp_dir()
            self.remove = True
        else:
            self.dir = expand(self.dir)

    def __enter__(self):
        if self.dir == ".":
            return

        _notice(self.quiet, "Entering directory {}", repr(get_absolute_path(self.dir)))

        make_dir(self.dir, quiet=True)

        self.prev_dir = change_dir(self.dir, quiet=True)

        return self.dir

    def __exit__(self, exc_type, exc_value, traceback):
        if self.dir == ".":
            return

        _debug(self.quiet, "Returning to directory {}", repr(get_absolute_path(self.prev_dir)))

        change_dir(self.prev_dir, quiet=True)

        if self.remove:
            remove(self.dir, quiet=True)

## Environment operations

def join_path_var(*paths):
    return _os.pathsep.join(unique(skip(paths)))

def get_current_dir():
    return _os.getcwd()

def get_home_dir(user=None):
    return _os.path.expanduser("~{}".format(user or ""))

def get_user():
    return _getpass.getuser()

def get_hostname():
    return _socket.gethostname()

def get_program_name(command=None):
    if command is None:
        args = ARGS
    else:
        args = command.split()

    for arg in args:
        if "=" not in arg:
            return get_base_name(arg)

def which(program_name):
    return _shutil.which(program_name)

def check_env(var, message=None):
    if var not in _os.environ:
        if message is None:
            message = "Environment variable {} is not set".format(repr(var))

        raise PlanoError(message)

def check_module(module, message=None):
    if _pkgutil.find_loader(module) is None:
        if message is None:
            message = "Python module {} is not found".format(repr(module))

        raise PlanoError(message)

def check_program(program, message=None):
    if which(program) is None:
        if message is None:
            message = "Program {} is not found".format(repr(program))

        raise PlanoError(message)

class working_env:
    def __init__(self, **vars):
        self.amend = vars.pop("amend", True)
        self.vars = vars

    def __enter__(self):
        self.prev_vars = dict(_os.environ)

        if not self.amend:
            for name, value in list(_os.environ.items()):
                if name not in self.vars:
                    del _os.environ[name]

        for name, value in self.vars.items():
            _os.environ[name] = str(value)

    def __exit__(self, exc_type, exc_value, traceback):
        for name, value in self.prev_vars.items():
            _os.environ[name] = value

        for name, value in self.vars.items():
            if name not in self.prev_vars:
                del _os.environ[name]

class working_module_path:
    def __init__(self, path, amend=True):
        if is_string(path):
            if not is_absolute(path):
                path = get_absolute_path(path)

            path = [path]

        if amend:
            path = path + _sys.path

        self.path = path

    def __enter__(self):
        self.prev_path = _sys.path
        _sys.path = self.path

    def __exit__(self, exc_type, exc_value, traceback):
        _sys.path = self.prev_path

def print_env(file=None):
    props = (
        ("ARGS", ARGS),
        ("ENV['PATH']", ENV.get("PATH")),
        ("ENV['PYTHONPATH']", ENV.get("PYTHONPATH")),
        ("sys.executable", _sys.executable),
        ("sys.path", _sys.path),
        ("sys.version", _sys.version.replace("\n", "")),
        ("get_current_dir()", get_current_dir()),
        ("get_home_dir()", get_home_dir()),
        ("get_hostname()", get_hostname()),
        ("get_program_name()", get_program_name()),
        ("get_user()", get_user()),
        ("plano.__file__", __file__),
        ("which('plano')", which("plano")),
    )

    print_properties(props, file=file)

def print_stack(file=None):
    _traceback.print_stack(file=file)

## File operations

def touch(file, quiet=False):
    file = expand(file)

    _notice(quiet, "Touching {}", repr(file))

    try:
        _os.utime(file, None)
    except OSError:
        append(file, "")

    return file

# symlinks=True - Preserve symlinks
# inside=True - Place from_path inside to_path if to_path is a directory
def copy(from_path, to_path, symlinks=True, inside=True, quiet=False):
    from_path = expand(from_path)
    to_path = expand(to_path)

    _notice(quiet, "Copying {} to {}", repr(from_path), repr(to_path))

    if is_dir(to_path) and inside:
        to_path = join(to_path, get_base_name(from_path))
    else:
        make_parent_dir(to_path, quiet=True)

    if is_link(from_path) and symlinks:
        make_link(to_path, read_link(from_path), quiet=True)
    elif is_dir(from_path):
        for name in list_dir(from_path):
            copy(join(from_path, name), join(to_path, name), symlinks=symlinks, inside=False, quiet=True)

        _shutil.copystat(from_path, to_path)
    else:
        _shutil.copy2(from_path, to_path)

    return to_path

# inside=True - Place from_path inside to_path if to_path is a directory
def move(from_path, to_path, inside=True, quiet=False):
    from_path = expand(from_path)
    to_path = expand(to_path)

    _notice(quiet, "Moving {} to {}", repr(from_path), repr(to_path))

    to_path = copy(from_path, to_path, inside=inside, quiet=True)
    remove(from_path, quiet=True)

    return to_path

def replace(path, replacement, quiet=False):
    path = expand(path)
    replacement = expand(replacement)

    _notice(quiet, "Replacing {} with {}", repr(path), repr(replacement))

    with temp_dir() as backup_dir:
        backup = join(backup_dir, "backup")
        backup_created = False

        if exists(path):
            move(path, backup, quiet=True)
            backup_created = True

        try:
            move(replacement, path, quiet=True)
        except OSError:
            notice("Removing")
            remove(path, quiet=True)

            if backup_created:
                move(backup, path, quiet=True)

            raise

        assert not exists(replacement), replacement
        assert exists(path), path

    return path

def remove(paths, quiet=False):
    if is_string(paths):
        paths = [paths]

    for path in paths:
        path = expand(path)

        if not exists(path):
            continue

        _debug(quiet, "Removing {}", repr(path))

        if is_dir(path):
            _shutil.rmtree(path, ignore_errors=True)
        else:
            _os.remove(path)

def get_file_size(file):
    file = expand(file)
    return _os.path.getsize(file)

## IO operations

def read(file):
    file = expand(file)

    with open(file) as f:
        return f.read()

def write(file, string):
    file = expand(file)

    make_parent_dir(file, quiet=True)

    with open(file, "w") as f:
        f.write(string)

    return file

def append(file, string):
    file = expand(file)

    make_parent_dir(file, quiet=True)

    with open(file, "a") as f:
        f.write(string)

    return file

def prepend(file, string):
    file = expand(file)

    orig = read(file)

    return write(file, string + orig)

def tail(file, count):
    file = expand(file)
    return "".join(tail_lines(file, count))

def read_lines(file):
    file = expand(file)

    with open(file) as f:
        return f.readlines()

def write_lines(file, lines):
    file = expand(file)

    make_parent_dir(file, quiet=True)

    with open(file, "w") as f:
        f.writelines(lines)

    return file

def append_lines(file, lines):
    file = expand(file)

    make_parent_dir(file, quiet=True)

    with open(file, "a") as f:
        f.writelines(lines)

    return file

def prepend_lines(file, lines):
    file = expand(file)

    orig_lines = read_lines(file)

    make_parent_dir(file, quiet=True)

    with open(file, "w") as f:
        f.writelines(lines)
        f.writelines(orig_lines)

    return file

def tail_lines(file, count):
    assert count >= 0, count

    lines = read_lines(file)

    return lines[-count:]

def string_replace_in_file(file, old, new, count=0):
    file = expand(file)
    return write(file, read(file).replace(old, new, count))

def concatenate(file, input_files):
    file = expand(file)

    assert file not in input_files

    make_parent_dir(file, quiet=True)

    with open(file, "wb") as f:
        for input_file in input_files:
            if not exists(input_file):
                continue

            with open(input_file, "rb") as inf:
                _shutil.copyfileobj(inf, f)

    return file

## Iterable operations

def unique(iterable):
    return list(dict.fromkeys(iterable).keys())

def skip(iterable, values=(None, "", (), [], {})):
    if is_scalar(values):
        values = [values]

    items = list()

    for item in iterable:
        if item not in values:
            items.append(item)

    return items

## JSON operations

def read_json(file):
    file = expand(file)

    with open(file) as f:
        return _json.load(f)

def write_json(file, data):
    file = expand(file)

    make_parent_dir(file, quiet=True)

    with open(file, "w") as f:
        _json.dump(data, f, indent=4, separators=(",", ": "), sort_keys=True)

    return file

def parse_json(json):
    return _json.loads(json)

def emit_json(data):
    return _json.dumps(data, indent=4, separators=(",", ": "), sort_keys=True)

def print_json(data, **kwargs):
    print(emit_json(data), **kwargs)

## HTTP operations

def _run_curl(method, url, content=None, content_file=None, content_type=None, output_file=None,
              insecure=False, user=None, password=None, client_cert=None, client_key=None, server_cert=None,
              quiet=False):
    check_program("curl")

    _notice(quiet, f"Sending {method} request to '{url}'")

    args = ["curl", "-sfL"]

    if method != "GET":
        args.extend(["-X", method])

    if content is not None:
        assert content_file is None
        args.extend(["-H", "Expect:", "-d", "@-"])

    if content_file is not None:
        assert content is None, content
        args.extend(["-H", "Expect:", "-d", f"@{content_file}"])

    if content_type is not None:
        args.extend(["-H", f"'Content-Type: {content_type}'"])

    if output_file is not None:
        args.extend(["-o", output_file])

    if insecure:
        args.append("--insecure")

    if user is not None:
        assert password is not None
        args.extend(["--user", f"{user}:{password}"])

    if client_cert is not None:
        args.extend(["--cert", client_cert])

    if client_key is not None:
        args.extend(["--key", client_key])

    if server_cert is not None:
        args.extend(["--cacert", server_cert])

    args.append(url)

    if output_file is not None:
        make_parent_dir(output_file, quiet=True)

    proc = run(args, stdin=_subprocess.PIPE, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
               input=content, check=False, quiet=True)

    if proc.exit_code > 0:
        raise PlanoProcessError(proc)

    if output_file is None:
        return proc.stdout_result

def http_get(url, output_file=None, insecure=False, user=None, password=None,
             client_cert=None, client_key=None, server_cert=None,
             quiet=False):
    return _run_curl("GET", url, output_file=output_file, insecure=insecure, user=user, password=password,
                     client_cert=client_cert, client_key=client_key, server_cert=server_cert,
                     quiet=quiet)

def http_get_json(url,
                  insecure=False, user=None, password=None,
                  client_cert=None, client_key=None, server_cert=None, quiet=False):
    return parse_json(http_get(url, insecure=insecure, user=user, password=password,
                               client_cert=client_cert, client_key=client_key, server_cert=server_cert,
                               quiet=quiet))

def http_put(url, content, content_type=None, insecure=False, user=None, password=None,
             client_cert=None, client_key=None, server_cert=None,
             quiet=False):
    _run_curl("PUT", url, content=content, content_type=content_type, insecure=insecure, user=user, password=password,
              client_cert=client_cert, client_key=client_key, server_cert=server_cert,
              quiet=quiet)

def http_put_file(url, content_file, content_type=None, insecure=False, user=None, password=None,
                  client_cert=None, client_key=None, server_cert=None,
                  quiet=False):
    _run_curl("PUT", url, content_file=content_file, content_type=content_type, insecure=insecure, user=user,
              password=password, client_cert=client_cert, client_key=client_key, server_cert=server_cert,
              quiet=quiet)

def http_put_json(url, data, insecure=False, user=None, password=None,
                  client_cert=None, client_key=None, server_cert=None,
                  quiet=False):
    http_put(url, emit_json(data), content_type="application/json", insecure=insecure, user=user, password=password,
             client_cert=client_cert, client_key=client_key, server_cert=server_cert,
             quiet=quiet)

def http_post(url, content, content_type=None, output_file=None, insecure=False, user=None, password=None,
              client_cert=None, client_key=None, server_cert=None,
              quiet=False):
    return _run_curl("POST", url, content=content, content_type=content_type, output_file=output_file,
                     insecure=insecure, user=user, password=password,
                     client_cert=client_cert, client_key=client_key, server_cert=server_cert,
                     quiet=quiet)

def http_post_file(url, content_file, content_type=None, output_file=None, insecure=False, user=None, password=None,
                   client_cert=None, client_key=None, server_cert=None,
                   quiet=False):
    return _run_curl("POST", url, content_file=content_file, content_type=content_type, output_file=output_file,
                     insecure=insecure, user=user, password=password,
                     client_cert=client_cert, client_key=client_key, server_cert=server_cert,
                     quiet=quiet)

def http_post_json(url, data, insecure=False, user=None, password=None,
                   client_cert=None, client_key=None, server_cert=None,
                   quiet=False):
    return parse_json(http_post(url, emit_json(data), content_type="application/json",
                                insecure=insecure, user=user, password=password,
                                client_cert=client_cert, client_key=client_key, server_cert=server_cert,
                                quiet=quiet))

## Link operations

def make_link(path: str, linked_path: str, quiet=False) -> str:
    _notice(quiet, "Making symlink {} to {}", repr(path), repr(linked_path))

    make_parent_dir(path, quiet=True)
    remove(path, quiet=True)

    _os.symlink(linked_path, path)

    return path

def read_link(path):
    return _os.readlink(path)

## Logging operations

_logging_levels = (
    "debug",
    "notice",
    "warning",
    "error",
    "disabled",
)

_DEBUG = _logging_levels.index("debug")
_NOTICE = _logging_levels.index("notice")
_WARNING = _logging_levels.index("warning")
_ERROR = _logging_levels.index("error")
_DISABLED = _logging_levels.index("disabled")

_logging_output = None
_logging_threshold = _NOTICE
_logging_contexts = list()

def enable_logging(level="notice", output=None, quiet=False):
    assert level in _logging_levels, level

    _notice(quiet, "Enabling logging (level={}, output={})", repr(level), repr(nvl(output, "stderr")))

    global _logging_threshold
    _logging_threshold = _logging_levels.index(level)

    if is_string(output):
        output = open(output, "w")

    global _logging_output
    _logging_output = output

def disable_logging(quiet=False):
    _notice(quiet, "Disabling logging")

    global _logging_threshold
    _logging_threshold = _DISABLED

class logging_enabled:
    def __init__(self, level="notice", output=None):
        self.level = level
        self.output = output

    def __enter__(self):
        self.prev_level = _logging_levels[_logging_threshold]
        self.prev_output = _logging_output

        if self.level == "disabled":
            disable_logging(quiet=True)
        else:
            enable_logging(level=self.level, output=self.output, quiet=True)

    def __exit__(self, exc_type, exc_value, traceback):
        if self.prev_level == "disabled":
            disable_logging(quiet=True)
        else:
            enable_logging(level=self.prev_level, output=self.prev_output, quiet=True)

class logging_disabled(logging_enabled):
    def __init__(self):
        super().__init__(level="disabled")

class logging_context:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        _logging_contexts.append(self.name)

    def __exit__(self, exc_type, exc_value, traceback):
        _logging_contexts.pop()

def fail(message, *args):
    if isinstance(message, BaseException):
        if not isinstance(message, PlanoError):
            error(message)

        raise message

    if args:
        message = message.format(*args)

    raise PlanoError(message)

def error(message, *args):
    log(_ERROR, message, *args)

def warning(message, *args):
    log(_WARNING, message, *args)

def notice(message, *args):
    log(_NOTICE, message, *args)

def debug(message, *args):
    log(_DEBUG, message, *args)

def log(level, message, *args):
    if is_string(level):
        level = _logging_levels.index(level)

    if _logging_threshold <= level:
        _print_message(level, message, args)

def _print_message(level, message, args):
    line = list()
    out = nvl(_logging_output, _sys.stderr)

    program_text = "{}:".format(get_program_name())

    line.append(cformat(program_text, color="gray"))

    level_text = "{}:".format(_logging_levels[level])
    level_color = ("white", "cyan", "yellow", "red", None)[level]
    level_bright = (False, False, False, True, False)[level]

    line.append(cformat(level_text, color=level_color, bright=level_bright))

    for name in _logging_contexts:
        line.append(cformat("{}:".format(name), color="yellow"))

    if isinstance(message, BaseException):
        exception = message

        line.append(str(exception))

        print(" ".join(line), file=out)

        if hasattr(exception, "__traceback__"):
            _traceback.print_exception(type(exception), exception, exception.__traceback__, file=out)
    else:
        message = str(message)

        if args:
            message = message.format(*args)

        line.append(capitalize(message))

        print(" ".join(line), file=out)

    out.flush()

def _notice(quiet, message, *args):
    if quiet:
        debug(message, *args)
    else:
        notice(message, *args)

def _debug(quiet, message, *args):
    if not quiet:
        debug(message, *args)

## Path operations

def expand(path):
    path = _os.path.expanduser(path)
    path = _os.path.expandvars(path)

    return path

def get_absolute_path(path):
    path = expand(path)
    return _os.path.abspath(path)

def normalize_path(path):
    path = expand(path)
    return _os.path.normpath(path)

def get_real_path(path):
    path = expand(path)
    return _os.path.realpath(path)

def get_relative_path(path, start=None):
    path = expand(path)
    return _os.path.relpath(path, start=start)

def get_file_url(path):
    path = expand(path)
    return "file:{}".format(get_absolute_path(path))

def exists(path):
    path = expand(path)
    return _os.path.lexists(path)

def is_absolute(path):
    path = expand(path)
    return _os.path.isabs(path)

def is_dir(path):
    path = expand(path)
    return _os.path.isdir(path)

def is_file(path):
    path = expand(path)
    return _os.path.isfile(path)

def is_link(path):
    path = expand(path)
    return _os.path.islink(path)

def join(*paths):
    paths = [expand(x) for x in paths]

    path = _os.path.join(*paths)
    path = normalize_path(path)

    return path

def split(path):
    path = expand(path)
    path = normalize_path(path)
    parent, child = _os.path.split(path)

    return parent, child

def split_extension(path):
    path = expand(path)
    path = normalize_path(path)
    root, ext = _os.path.splitext(path)

    return root, ext

def get_parent_dir(path):
    path = expand(path)
    path = normalize_path(path)
    parent, child = split(path)

    return parent

def get_base_name(path):
    path = expand(path)
    path = normalize_path(path)
    parent, name = split(path)

    return name

def get_name_stem(file):
    file = expand(file)
    name = get_base_name(file)

    if name.endswith(".tar.gz"):
        name = name[:-3]

    stem, ext = split_extension(name)

    return stem

def get_name_extension(file):
    file = expand(file)
    name = get_base_name(file)
    stem, ext = split_extension(name)

    return ext

def _check_path(path, test_func, message):
    path = expand(path)

    if not test_func(path):
        parent_dir = get_parent_dir(path)

        if is_dir(parent_dir):
            found_paths = ", ".join([repr(x) for x in list_dir(parent_dir)])
            message = "{}. The parent directory contains: {}".format(message.format(repr(path)), found_paths)
        else:
            message = "{}".format(message.format(repr(path)))

        raise PlanoError(message)

def check_exists(path):
    path = expand(path)
    _check_path(path, exists, "File or directory {} not found")

def check_file(path):
    path = expand(path)
    _check_path(path, is_file, "File {} not found")

def check_dir(path):
    path = expand(path)
    _check_path(path, is_dir, "Directory {} not found")

def await_exists(path, timeout=30, quiet=False):
    path = expand(path)

    _notice(quiet, "Waiting for path {} to exist", repr(path))

    timeout_message = "Timed out waiting for path {} to exist".format(path)
    period = 0.03125

    with Timer(timeout=timeout, timeout_message=timeout_message) as timer:
        while True:
            try:
                check_exists(path)
            except PlanoError:
                sleep(period, quiet=True)
                period = min(1, period * 2)
            else:
                return

## Port operations

def get_random_port(min=49152, max=65535):
    ports = [_random.randint(min, max) for _ in range(3)]

    for port in ports:
        try:
            check_port(port)
        except PlanoError:
            return port

    raise PlanoError("Random ports unavailable")

def check_port(port, host="localhost"):
    sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)

    if sock.connect_ex((host, port)) != 0:
        raise PlanoError("Port {} (host {}) is not reachable".format(repr(port), repr(host)))

def await_port(port, host="localhost", timeout=30, quiet=False):
    _notice(quiet, "Waiting for port {}", port)

    if is_string(port):
        port = int(port)

    timeout_message = "Timed out waiting for port {} to open".format(port)
    period = 0.03125

    with Timer(timeout=timeout, timeout_message=timeout_message) as timer:
        while True:
            try:
                check_port(port, host=host)
            except PlanoError:
                sleep(period, quiet=True)
                period = min(1, period * 2)
            else:
                return

## Process operations

def get_process_id():
    return _os.getpid()

def _format_command(command, represent=True):
    if is_string(command):
        args = _shlex.split(command)
    else:
        args = command

    args = [expand(str(x)) for x in args]
    command = " ".join(args)

    if represent:
        return repr(command)
    else:
        return command

# quiet=False - Don't log at notice level
# stash=False - No output unless there is an error
# output=<file> - Send stdout and stderr to a file
# stdin=<file> - XXX
# stdout=<file> - Send stdout to a file
# stderr=<file> - Send stderr to a file
# shell=False - XXX
def start(command, stdin=None, stdout=None, stderr=None, output=None, shell=False, stash=False, quiet=False):
    _notice(quiet, "Starting a new process (command {})", _format_command(command))

    if output is not None:
        stdout, stderr = output, output

    if is_string(stdin):
        stdin = expand(stdin)
        stdin = open(stdin, "r")

    if is_string(stdout):
        stdout = expand(stdout)
        stdout = open(stdout, "w")

    if is_string(stderr):
        stderr = expand(stderr)
        stderr = open(stderr, "w")

    if stdin is None:
        stdin = _sys.stdin

    if stdout is None:
        stdout = _sys.stdout

    if stderr is None:
        stderr = _sys.stderr

    stash_file = None

    if stash:
        stash_file = make_temp_file()
        out = open(stash_file, "w")
        stdout = out
        stderr = out

    if shell:
        if is_string(command):
            args = command
        else:
            args = " ".join(map(str, command))
    else:
        if is_string(command):
            args = _shlex.split(command)
        else:
            args = command

        args = [expand(str(x)) for x in args]

    try:
        proc = PlanoProcess(args, stdin=stdin, stdout=stdout, stderr=stderr, shell=shell, close_fds=True, stash_file=stash_file)
    except OSError as e:
        raise PlanoError("Command {}: {}".format(_format_command(command), str(e)))

    _notice(quiet, "{} started", proc)

    return proc

def stop(proc, timeout=None, quiet=False):
    _notice(quiet, "Stopping {}", proc)

    if proc.poll() is not None:
        if proc.exit_code == 0:
            debug("{} already exited normally", proc)
        elif proc.exit_code == -(_signal.SIGTERM):
            debug("{} was already terminated", proc)
        else:
            debug("{} already exited with code {}", proc, proc.exit_code)

        return proc

    kill(proc, quiet=True)

    return wait(proc, timeout=timeout, quiet=True)

def kill(proc, quiet=False):
    _notice(quiet, "Killing {}", proc)

    proc.terminate()

def wait(proc, timeout=None, check=False, quiet=False):
    _notice(quiet, "Waiting for {} to exit", proc)

    try:
        proc.wait(timeout=timeout)
    except _subprocess.TimeoutExpired:
        error("{} timed out after {} seconds", proc, timeout)
        raise PlanoTimeout()

    if proc.exit_code == 0:
        debug("{} exited normally", proc)
    elif proc.exit_code < 0:
        debug("{} was terminated by signal {}", proc, abs(proc.exit_code))
    else:
        if check:
            error("{} exited with code {}", proc, proc.exit_code)
        else:
            debug("{} exited with code {}", proc, proc.exit_code)

    if proc.stash_file is not None:
        if proc.exit_code > 0:
            eprint(read(proc.stash_file), end="")

        if not WINDOWS:
            remove(proc.stash_file, quiet=True)

    if check and proc.exit_code > 0:
        raise PlanoProcessError(proc)

    return proc

# input=<string> - Pipe <string> to the process
def run(command, stdin=None, stdout=None, stderr=None, input=None, output=None,
        stash=False, shell=False, check=True, quiet=False):
    _notice(quiet, "Running command {}", _format_command(command))

    if input is not None:
        assert stdin in (None, _subprocess.PIPE), stdin

        input = input.encode("utf-8")
        stdin = _subprocess.PIPE

    proc = start(command, stdin=stdin, stdout=stdout, stderr=stderr, output=output,
                 stash=stash, shell=shell, quiet=True)

    proc.stdout_result, proc.stderr_result = proc.communicate(input=input)

    if proc.stdout_result is not None:
        proc.stdout_result = proc.stdout_result.decode("utf-8")

    if proc.stderr_result is not None:
        proc.stderr_result = proc.stderr_result.decode("utf-8")

    return wait(proc, check=check, quiet=True)

# input=<string> - Pipe the given input into the process
def call(command, input=None, shell=False, quiet=False):
    _notice(quiet, "Calling {}", _format_command(command))

    proc = run(command, stdin=_subprocess.PIPE, stdout=_subprocess.PIPE, stderr=_subprocess.PIPE,
               input=input, shell=shell, check=True, quiet=True)

    return proc.stdout_result

def exit(arg=None, *args, **kwargs):
    verbose = kwargs.get("verbose", False)

    if arg in (0, None):
        if verbose:
            notice("Exiting normally")

        _sys.exit()

    if is_string(arg):
        if args:
            arg = arg.format(*args)

        if verbose:
            error(arg)

        _sys.exit(arg)

    if isinstance(arg, BaseException):
        if verbose:
            error(arg)

        _sys.exit(str(arg))

    if isinstance(arg, int):
        _sys.exit(arg)

    raise PlanoException("Illegal argument")

_child_processes = list()

class PlanoProcess(_subprocess.Popen):
    def __init__(self, args, **options):
        self.stash_file = options.pop("stash_file", None)

        super().__init__(args, **options)

        self.args = args
        self.stdout_result = None
        self.stderr_result = None

        _child_processes.append(self)

    @property
    def exit_code(self):
        return self.returncode

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        stop(self)

    def __repr__(self):
        return "process {} (command {})".format(self.pid, _format_command(self.args))

class PlanoProcessError(_subprocess.CalledProcessError, PlanoError):
    def __init__(self, proc):
        super().__init__(proc.exit_code, _format_command(proc.args, represent=False))

def _default_sigterm_handler(signum, frame):
    for proc in _child_processes:
        if proc.poll() is None:
            kill(proc, quiet=True)

    exit(-(_signal.SIGTERM))

_signal.signal(_signal.SIGTERM, _default_sigterm_handler)

## String operations

def string_replace_re(string, pattern, replacement, count=0):
    return _re.sub(pattern, replacement, string, count)

def string_matches_re(string, pattern):
    return _re.search(pattern, string) is not None

def string_matches_glob(string, pattern):
    return _fnmatch.fnmatchcase(string, pattern)

def shorten(string, max, ellipsis=None):
    assert max is None or isinstance(max, int)

    if string is None:
        return ""

    if max is None or len(string) < max:
        return string
    else:
        if ellipsis is not None:
            string = string + ellipsis
            end = _max(0, max - len(ellipsis))
            return string[0:end] + ellipsis
        else:
            return string[0:max]

def plural(noun, count=0, plural=None):
    if noun in (None, ""):
        return ""

    if count == 1:
        return noun

    if plural is None:
        if noun.endswith("s"):
            plural = "{}ses".format(noun)
        else:
            plural = "{}s".format(noun)

    return plural

def capitalize(string):
    if not string:
        return ""

    return string[0].upper() + string[1:]

def base64_encode(string):
    return _base64.b64encode(string)

def base64_decode(string):
    return _base64.b64decode(string)

def url_encode(string):
    return _urllib_parse.quote_plus(string)

def url_decode(string):
    return _urllib_parse.unquote_plus(string)

def parse_url(url):
    return _urllib_parse.urlparse(url)

# A class for building up long strings
#
# append = StringBuilder()
# append("abc")
# append()
# append("123")
# str(append) -> "abc\n\n123"
class StringBuilder:
    def __init__(self):
        self._items = list()

    def __call__(self, item=""):
        self.append(item=item)

    def __str__(self):
        return self.join()

    def append(self, item=""):
        assert item is not None
        self._items.append(str(item))

    def join(self, separator="\n"):
        return separator.join(self._items)

    def write(self, file, separator="\n"):
        return write(file, self.join(separator=separator))

    def clear(self):
        self._items.clear()

## Temp operations

def get_system_temp_dir():
    return _tempfile.gettempdir()

def get_user_temp_dir():
    try:
        return _os.environ["XDG_RUNTIME_DIR"]
    except KeyError:
        return join(get_system_temp_dir(), get_user())

def make_temp_file(prefix="plano-", suffix="", dir=None):
    if dir is None:
        dir = get_system_temp_dir()

    return _tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=dir)[1]

def make_temp_dir(prefix="plano-", suffix="", dir=None):
    if dir is None:
        dir = get_system_temp_dir()

    return _tempfile.mkdtemp(prefix=prefix, suffix=suffix, dir=dir)

class temp_file:
    def __init__(self, prefix="plano-", suffix="", dir=None):
        if dir is None:
            dir = get_system_temp_dir()

        self.fd, self.file = _tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=dir)

    def __enter__(self):
        return self.file

    def __exit__(self, exc_type, exc_value, traceback):
        _os.close(self.fd)

        if not WINDOWS: # XXX
            remove(self.file, quiet=True)

class temp_dir:
    def __init__(self, prefix="plano-", suffix="", dir=None):
        self.dir = make_temp_dir(prefix=prefix, suffix=suffix, dir=dir)

    def __enter__(self):
        return self.dir

    def __exit__(self, exc_type, exc_value, traceback):
        remove(self.dir, quiet=True)

## Time operations

# Unix time
def get_time():
    return _time.time()

# Python UTC time
def get_datetime():
    return _datetime.datetime.now(tz=_datetime.timezone.utc)

def parse_timestamp(timestamp, format="%Y-%m-%dT%H:%M:%SZ"):
    if timestamp is None:
        return None

    datetime = _datetime.datetime.strptime(timestamp, format)
    datetime = datetime.replace(tzinfo=_datetime.timezone.utc)

    return datetime

def format_timestamp(datetime=None, format="%Y-%m-%dT%H:%M:%SZ"):
    if datetime is None:
        datetime = get_datetime()

    return datetime.strftime(format)

def format_date(datetime=None):
    if datetime is None:
        datetime = get_datetime()

    day = datetime.day
    month = datetime.strftime("%B")
    year = datetime.strftime("%Y")

    return f"{day} {month} {year}"

def format_time(datetime=None, precision="second"):
    if datetime is None:
        datetime = get_datetime()

    assert precision in ("minute", "second"), "Illegal precision value"

    hour = datetime.hour
    minute = datetime.strftime("%M")
    second = datetime.strftime("%S")

    if precision == "second":
        return f"{hour}:{minute}:{second}"
    else:
        return f"{hour}:{minute}"

def format_duration(seconds, align=False):
    assert seconds >= 0

    if seconds >= 3600:
        value = seconds / 3600
        unit = "h"
    elif seconds >= 5 * 60:
        value = seconds / 60
        unit = "m"
    else:
        value = seconds
        unit = "s"

    if align:
        return "{:.1f}{}".format(value, unit)
    elif value > 10:
        return "{:.0f}{}".format(value, unit)
    else:
        return "{:.1f}".format(value).removesuffix(".0") + unit

def sleep(seconds, quiet=False):
    _notice(quiet, "Sleeping for {} {}", seconds, plural("second", seconds))

    _time.sleep(seconds)

class Timer:
    def __init__(self, timeout=None, timeout_message=None):
        self.timeout = timeout
        self.timeout_message = timeout_message

        if self.timeout is not None and not hasattr(_signal, "SIGALRM"): # pragma: nocover
            self.timeout = None

        self.start_time = None
        self.stop_time = None

    def start(self):
        self.start_time = get_time()

        if self.timeout is not None:
            self.prev_handler = _signal.signal(_signal.SIGALRM, self.raise_timeout)
            self.prev_timeout, prev_interval = _signal.setitimer(_signal.ITIMER_REAL, self.timeout)
            self.prev_timer_suspend_time = get_time()

            assert prev_interval == 0.0, "This case is not yet handled"

    def stop(self):
        self.stop_time = get_time()

        if self.timeout is not None:
            assert get_time() - self.prev_timer_suspend_time > 0, "This case is not yet handled"

            _signal.signal(_signal.SIGALRM, self.prev_handler)
            _signal.setitimer(_signal.ITIMER_REAL, self.prev_timeout)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

    @property
    def elapsed_time(self):
        assert self.start_time is not None

        if self.stop_time is None:
            return get_time() - self.start_time
        else:
            return self.stop_time - self.start_time

    def raise_timeout(self, *args):
        raise PlanoTimeout(self.timeout_message)

## Unique ID operations

# Length in bytes, renders twice as long in hex
def get_unique_id(bytes=16):
    assert bytes >= 1
    assert bytes <= 16

    uuid_bytes = _uuid.uuid4().bytes
    uuid_bytes = uuid_bytes[:bytes]

    return _binascii.hexlify(uuid_bytes).decode("utf-8")

## Value operations

def nvl(value, replacement):
    if value is None:
        return replacement

    return value

def is_string(value):
    return isinstance(value, str)

def is_scalar(value):
    return value is None or isinstance(value, (str, int, float, complex, bool))

def is_empty(value):
    return value in (None, "", (), [], {})

def pformat(value):
    return _pprint.pformat(value, width=120)

def format_empty(value, replacement):
    if is_empty(value):
        value = replacement

    return value

def format_not_empty(value, template=None):
    if not is_empty(value) and template is not None:
        value = template.format(value)

    return value

def format_repr(obj, limit=None):
    attrs = ["{}={}".format(k, repr(v)) for k, v in obj.__dict__.items()]
    return "{}({})".format(obj.__class__.__name__, ", ".join(attrs[:limit]))

class Namespace:
    def __init__(self, **kwargs):
        for name in kwargs:
            setattr(self, name, kwargs[name])

    def __eq__(self, other):
        return vars(self) == vars(other)

    def __contains__(self, key):
        return key in self.__dict__

    def __repr__(self):
        return format_repr(self)

## YAML operations

def read_yaml(file):
    check_module("yaml", "Python module 'yaml' is not found.  To install it, run 'pip install pyyaml'.")

    import yaml as _yaml

    file = expand(file)

    with open(file) as f:
        return _yaml.safe_load(f)

def write_yaml(file, data):
    check_module("yaml", "Python module 'yaml' is not found.  To install it, run 'pip install pyyaml'.")

    import yaml as _yaml

    file = expand(file)

    make_parent_dir(file, quiet=True)

    with open(file, "w") as f:
        _yaml.safe_dump(data, f)

    return file

def parse_yaml(yaml):
    check_module("yaml", "Python module 'yaml' is not found.  To install it, run 'pip install pyyaml'.")

    import yaml as _yaml

    return _yaml.safe_load(yaml)

def emit_yaml(data):
    check_module("yaml", "Python module 'yaml' is not found.  To install it, run 'pip install pyyaml'.")

    import yaml as _yaml

    return _yaml.safe_dump(data)

def print_yaml(data, **kwargs):
    print(emit_yaml(data), **kwargs)

if PLANO_DEBUG: # pragma: nocover
    enable_logging(level="debug")
