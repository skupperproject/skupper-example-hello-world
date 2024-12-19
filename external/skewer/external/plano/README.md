# Plano

[![main](https://github.com/ssorj/plano/workflows/main/badge.svg)](https://github.com/ssorj/plano/actions?query=workflow%3Amain)

Python functions for writing shell-style system scripts.

## Installation

Install the dependencies if you need to:

~~~
sudo dnf -y install python-build python-pip python-pyyaml
~~~

Install plano globally for the current user:

~~~
make install
~~~

## A self-contained command with subcommands

`~/.local/bin/widget`:
~~~ python
#!/usr/bin/python

import sys
from plano import *

@command
def greeting(message="Howdy"):
    print(message)

if __name__ == "__main__":
    PlanoCommand(sys.modules[__name__]).main()
~~~

~~~ shell
$ widget greeting --message Hello
--> greeting
Hello
<-- greeting
OK (0s)
~~~

## A self-contained test command

`~/.local/bin/widget-test`:
~~~ python
import sys
from plano import *

@test
def check():
    run("widget greeting --message Yo")

if __name__ == "__main__":
    PlanoTestCommand(sys.modules[__name__]).main()
~~~

~~~ shell
$ widget-test
=== Configuration ===
Modules:        __main__
Test timeout:   5m
Fail fast:      False

=== Module '__main__' ===
check ........................................................... PASSED   0.0s

=== Summary ===
Total:     1
Skipped:   0
Failed:    0

=== RESULT ===
All tests passed
~~~

## Programmatic test definition

~~~ python
from plano import *

def test_widget(message):
    run(f"widget greeting --message {message}")

for message in "hi", "lo", "in between":
    add_test(f"message-{message}", test_widget, message)
~~~

## Things to know

* The plano command accepts command sequences in the form "this,that"
  (no spaces).  The command arguments are applied to the last command
  only.

## Dependencies

PyYAML:

~~~
pip install pyyaml
~~~

## Setting up Plano as an embedded dependency

Change directory to the root of your project:

~~~ console
cd <project-dir>/
~~~

Add the Plano code as a subdirectory:

~~~ shell
mkdir -p external
curl -sfL https://github.com/ssorj/plano/archive/main.tar.gz | tar -C external -xz
mv external/plano-main external/plano
~~~

Symlink the Plano library into your `python` directory:

~~~ shell
mkdir -p python
ln -s ../external/plano/src/plano python/plano
~~~

Copy the `plano` command into the root of your project:

~~~ shell
cp external/plano/bin/plano plano
~~~

Optionally, add a command to `.plano.py` to update the embedded Plano:

~~~ python
from plano.github import *

@command
def update_plano():
    """
    Update the embedded Plano repo
    """
    update_external_from_github("external/plano", "ssorj", "plano")
~~~

## Extending an existing command

~~~ python
@command(parent=blammo)
def blammo(*args, **kwargs):
    parent(*args, **kwargs)
    # Do child stuff
~~~
