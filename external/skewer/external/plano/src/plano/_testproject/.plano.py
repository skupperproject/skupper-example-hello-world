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

from plano import *

@command
def base_command(alpha, beta, omega="x"):
    """
    Base command help
    """

    print("base", alpha, beta, omega)

@command(name="extended-command", parent=base_command)
def extended_command(alpha, beta, omega="y"):
    print("extended", alpha, omega)
    parent(alpha, beta, omega)

@command(parameters=[CommandParameter("message_", help="The message to print", display_name="message"),
                     CommandParameter("count", help="Print the message COUNT times"),
                     CommandParameter("extra", default=1, short_option="e")])
def echo(message_, count=1, extra=None, trouble=False, verbose=False):
    """
    Print a message to the console
    """

    print("Echoing (message={}, count={})".format(message_, count))

    if trouble:
        raise Exception("Trouble")

    for i in range(count):
       print(message_)

@command
def echoecho(message):
    echo(message)

@command
def haberdash(first, *middle, last="bowler"):
    """
    Habberdash command help
    """

    data = [first, *middle, last]
    write_json("haberdash.json", data)

@command(parameters=[CommandParameter("optional", positional=True)])
def balderdash(required, optional="malarkey", other="rubbish", **extra_kwargs):
    """
    Balderdash command help
    """

    data = [required, optional, other]
    write_json("balderdash.json", data)

@command
def splasher():
    write_json("splasher.json", [1])

@command
def dasher(alpha, beta=123):
    pass

@command(passthrough=True)
def dancer(gamma, omega="abc", passthrough_args=[]):
    write_json("dancer.json", passthrough_args)

# Vixen's parent calls prancer.  We are testing to ensure the extended
# prancer (below) is executed.

from plano._tests import prancer, vixen

@command(parent=prancer)
def prancer():
    parent()

    notice("Extended prancer")

    write_json("prancer.json", True)

@command(parent=vixen)
def vixen():
    parent()

@command
def no_parent():
    parent()

@command(parameters=[CommandParameter("spinach")])
def feta(*args, **kwargs):
    write_json("feta.json", kwargs["spinach"])

@command(hidden=True)
def invisible(something="nothing"):
    write_json("invisible.json", something)
