How to Install Hector
=======================================

******************
Install Script
******************
::

        $ ./install.sh

There is an install script in the base of Hector's root directory.
Which will attempt to install the dependencies for running cassandra, python dependencies, then downloading 
the latest apache cassandra version it is aware of to /var/lib/cassandra.
Using This method hector's agent.py should just run.::

       $ pip -r requirements.txt

Optionally to install just the python dependencies. Though you may need to modify the settings/config.py::

       $ easy_install pip

To install pip, consult your distribution documentation on installing python setuptools.

