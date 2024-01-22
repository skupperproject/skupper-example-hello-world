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

from .main import *
from .command import *

import argparse as _argparse
import asyncio as _asyncio
import fnmatch as _fnmatch
import functools as _functools
import importlib as _importlib
import inspect as _inspect
import sys as _sys
import traceback as _traceback

class PlanoTestCommand(BaseCommand):
    def __init__(self, test_modules=[]):
        self.test_modules = test_modules

        if _inspect.ismodule(self.test_modules):
            self.test_modules = [self.test_modules]

        self.parser = BaseArgumentParser()
        self.parser.add_argument("include", metavar="PATTERN", nargs="*", default=["*"],
                                 help="Run tests with names matching PATTERN (default '*', all tests)")
        self.parser.add_argument("-e", "--exclude", metavar="PATTERN", action="append", default=[],
                                 help="Do not run tests with names matching PATTERN (repeatable)")
        self.parser.add_argument("-m", "--module", action="append", default=[],
                                 help="Collect tests from MODULE (repeatable)")
        self.parser.add_argument("-l", "--list", action="store_true",
                                 help="Print the test names and exit")
        self.parser.add_argument("--enable", metavar="PATTERN", action="append", default=[],
                                 help=_argparse.SUPPRESS)
        self.parser.add_argument("--unskip", metavar="PATTERN", action="append", default=[],
                                 help="Run skipped tests matching PATTERN (repeatable)")
        self.parser.add_argument("--timeout", metavar="SECONDS", type=int, default=300,
                                 help="Fail any test running longer than SECONDS (default 300)")
        self.parser.add_argument("--fail-fast", action="store_true",
                                 help="Exit on the first failure encountered in a test run")
        self.parser.add_argument("--iterations", metavar="COUNT", type=int, default=1,
                                 help="Run the tests COUNT times (default 1)")
        self.parser.add_argument("--verbose", action="store_true",
                                 help="Print detailed logging to the console")
        self.parser.add_argument("--quiet", action="store_true",
                                 help="Print no logging to the console")

    def parse_args(self, args):
        return self.parser.parse_args(args)

    def configure_logging(self, args):
        if args.verbose:
            return "notice", None

        if args.quiet:
            return "error", None

        return "warning", None

    def init(self, args):
        self.list_only = args.list
        self.include_patterns = args.include
        self.exclude_patterns = args.exclude
        self.enable_patterns = args.enable
        self.unskip_patterns = args.unskip
        self.timeout = args.timeout
        self.fail_fast = args.fail_fast
        self.iterations = args.iterations
        self.verbose = args.verbose
        self.quiet = args.quiet

        try:
            for name in args.module:
                self.test_modules.append(_importlib.import_module(name))
        except ImportError as e:
            raise PlanoError(e)

    def run(self):
        if self.list_only:
            print_tests(self.test_modules)
            return

        for i in range(self.iterations):
            run_tests(self.test_modules, include=self.include_patterns,
                      exclude=self.exclude_patterns,
                      enable=self.enable_patterns, unskip=self.unskip_patterns,
                      test_timeout=self.timeout, fail_fast=self.fail_fast,
                      verbose=self.verbose, quiet=self.quiet)

class PlanoTestSkipped(Exception):
    pass

def test(_function=None, name=None, module=None, timeout=None, disabled=False):
    class Test:
        def __init__(self, function):
            self.function = function
            self.name = name
            self.module = module
            self.timeout = timeout
            self.disabled = disabled

            if self.name is None:
                self.name = self.function.__name__.strip("_").replace("_", "-")

            if self.module is None:
                self.module = _inspect.getmodule(self.function)

            if not hasattr(self.module, "_plano_tests"):
                self.module._plano_tests = list()

            self.module._plano_tests.append(self)

        def __call__(self, test_run, unskipped):
            try:
                ret = self.function()

                if _inspect.iscoroutine(ret):
                    _asyncio.run(ret)
            except SystemExit as e:
                error(e)
                raise PlanoError("System exit with code {}".format(e))

        def __repr__(self):
            return "test '{}:{}'".format(self.module.__name__, self.name)

    if _function is None:
        return Test
    else:
        return Test(_function)

def add_test(name, func, *args, **kwargs):
    test(_functools.partial(func, *args, **kwargs), name=name, module=_inspect.getmodule(func))

def skip_test(reason=None):
    if _inspect.stack()[2].frame.f_locals["unskipped"]:
        return

    raise PlanoTestSkipped(reason)

class expect_exception:
    def __init__(self, exception_type=Exception, contains=None):
        self.exception_type = exception_type
        self.contains = contains

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is None:
            assert False, "Never encountered expected exception {}".format(self.exception_type.__name__)

        if self.contains is None:
            return isinstance(exc_value, self.exception_type)
        else:
            return isinstance(exc_value, self.exception_type) and self.contains in str(exc_value)

class expect_error(expect_exception):
    def __init__(self, contains=None):
        super().__init__(PlanoError, contains=contains)

class expect_timeout(expect_exception):
    def __init__(self, contains=None):
        super().__init__(PlanoTimeout, contains=contains)

class expect_system_exit(expect_exception):
    def __init__(self, contains=None):
        super().__init__(SystemExit, contains=contains)

class expect_output(temp_file):
    def __init__(self, equals=None, contains=None, startswith=None, endswith=None):
        super().__init__()
        self.equals = equals
        self.contains = contains
        self.startswith = startswith
        self.endswith = endswith

    def __exit__(self, exc_type, exc_value, traceback):
        result = read(self.file)

        if self.equals is None:
            assert len(result) > 0, result
        else:
            assert result == self.equals, result

        if self.contains is not None:
            assert self.contains in result, result

        if self.startswith is not None:
            assert result.startswith(self.startswith), result

        if self.endswith is not None:
            assert result.endswith(self.endswith), result

        super().__exit__(exc_type, exc_value, traceback)

def print_tests(modules):
    if _inspect.ismodule(modules):
        modules = (modules,)

    for module in modules:
        for test in module._plano_tests:
            flags = "(disabled)" if test.disabled else ""
            print(" ".join((str(test), flags)).strip())

def run_tests(modules, include="*", exclude=(), enable=(), unskip=(), test_timeout=300,
              fail_fast=False, verbose=False, quiet=False):
    if _inspect.ismodule(modules):
        modules = (modules,)

    if is_string(include):
        include = (include,)

    if is_string(exclude):
        exclude = (exclude,)

    if is_string(enable):
        enable = (enable,)

    if is_string(unskip):
        enable = (unskip,)

    test_run = TestRun(test_timeout=test_timeout, fail_fast=fail_fast, verbose=verbose, quiet=quiet)

    if verbose:
        notice("Starting {}", test_run)
    elif not quiet:
        cprint("=== Configuration ===", color="cyan")

        props = (
            ("Modules", format_empty(", ".join([x.__name__ for x in modules]), "[none]")),
            ("Test timeout", format_duration(test_timeout)),
            ("Fail fast", fail_fast),
        )

        print_properties(props)
        print()

    stop = False

    for module in modules:
        if stop:
            break

        if verbose:
            notice("Running tests from module {} (file {})", repr(module.__name__), repr(module.__file__))
        elif not quiet:
            cprint("=== Module {} ===".format(repr(module.__name__)), color="cyan")

        if not hasattr(module, "_plano_tests"):
            warning("Module {} has no tests", repr(module.__name__))
            continue

        for test in module._plano_tests:
            if stop:
                break

            if test.disabled and not any([_fnmatch.fnmatchcase(test.name, x) for x in enable]):
                continue

            included = any([_fnmatch.fnmatchcase(test.name, x) for x in include])
            excluded = any([_fnmatch.fnmatchcase(test.name, x) for x in exclude])
            unskipped = any([_fnmatch.fnmatchcase(test.name, x) for x in unskip])

            if included and not excluded:
                test_run.tests.append(test)
                stop = _run_test(test_run, test, unskipped)

        if not verbose and not quiet:
            print()

    total = len(test_run.tests)
    skipped = len(test_run.skipped_tests)
    failed = len(test_run.failed_tests)

    if total == 0:
        raise PlanoError("No tests ran")

    notes = ""

    if skipped != 0:
        notes = "({} skipped)".format(skipped)

    if failed == 0:
        result_message = "All tests passed {}".format(notes).strip()
    else:
        result_message = "{} {} failed {}".format(failed, plural("test", failed), notes).strip()

    if verbose:
        if failed == 0:
            notice(result_message)
        else:
            error(result_message)
    elif not quiet:
        cprint("=== Summary ===", color="cyan")

        props = (
            ("Total", total),
            ("Skipped", skipped, format_not_empty(", ".join([x.name for x in test_run.skipped_tests]), "({})")),
            ("Failed", failed, format_not_empty(", ".join([x.name for x in test_run.failed_tests]), "({})")),
        )

        print_properties(props)
        print()

        cprint("=== RESULT ===", color="cyan")

        if failed == 0:
            cprint(result_message, color="green")
        else:
            cprint(result_message, color="red", bright="True")

        print()

    if failed != 0:
        raise PlanoError(result_message)

def _run_test(test_run, test, unskipped):
    if test_run.verbose:
        notice("Running {}", test)
    elif not test_run.quiet:
        print("{:.<65} ".format(test.name + " "), end="")

    timeout = nvl(test.timeout, test_run.test_timeout)

    with temp_file() as output_file:
        try:
            with Timer(timeout=timeout) as timer:
                if test_run.verbose:
                    test(test_run, unskipped)
                else:
                    with output_redirected(output_file, quiet=True):
                        test(test_run, unskipped)
        except KeyboardInterrupt:
            raise
        except PlanoTestSkipped as e:
            test_run.skipped_tests.append(test)

            if test_run.verbose:
                notice("{} SKIPPED ({})", test, format_duration(timer.elapsed_time))
            elif not test_run.quiet:
                _print_test_result("SKIPPED", timer, "yellow")
                print("Reason: {}".format(str(e)))
        except Exception as e:
            test_run.failed_tests.append(test)

            if test_run.verbose:
                _traceback.print_exc()

                if isinstance(e, PlanoTimeout):
                    error("{} **FAILED** (TIMEOUT) ({})", test, format_duration(timer.elapsed_time))
                else:
                    error("{} **FAILED** ({})", test, format_duration(timer.elapsed_time))
            elif not test_run.quiet:
                if isinstance(e, PlanoTimeout):
                    _print_test_result("**FAILED** (TIMEOUT)", timer, color="red", bright=True)
                else:
                    _print_test_result("**FAILED**", timer, color="red", bright=True)

                _print_test_error(e)
                _print_test_output(output_file)

            if test_run.fail_fast:
                return True
        else:
            test_run.passed_tests.append(test)

            if test_run.verbose:
                notice("{} PASSED ({})", test, format_duration(timer.elapsed_time))
            elif not test_run.quiet:
                _print_test_result("PASSED", timer)

def _print_test_result(status, timer, color="white", bright=False):
    cprint("{:<7}".format(status), color=color, bright=bright, end="")
    print("{:>6}".format(format_duration(timer.elapsed_time, align=True)))

def _print_test_error(e):
    cprint("--- Error ---", color="yellow")

    if isinstance(e, PlanoProcessError):
        print("> {}".format(str(e)))
    else:
        lines = _traceback.format_exc().rstrip().split("\n")
        lines = ["> {}".format(x) for x in lines]

        print("\n".join(lines))

def _print_test_output(output_file):
    if get_file_size(output_file) == 0:
        return

    cprint("--- Output ---", color="yellow")

    with open(output_file, "r") as out:
        for line in out:
            print("> {}".format(line), end="")

class TestRun:
    def __init__(self, test_timeout=None, fail_fast=False, verbose=False, quiet=False):
        self.test_timeout = test_timeout
        self.fail_fast = fail_fast
        self.verbose = verbose
        self.quiet = quiet

        self.tests = list()
        self.skipped_tests = list()
        self.failed_tests = list()
        self.passed_tests = list()

    def __repr__(self):
        return format_repr(self)

def _main(): # pragma: nocover
    PlanoTestCommand().main()
