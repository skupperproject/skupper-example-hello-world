# Plano

[![main](https://github.com/ssorj/plano/workflows/main/badge.svg)](https://github.com/ssorj/plano/actions?query=workflow%3Amain)

Python functions for writing shell-style system scripts.

## Installation

To install plano globally for the current user:

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
