How to Use Hector From the Command Line
=======================================

Using Hector from the Command Line::

        $ hector --help
           optional arguments:
             -h, --help            show this help message and exit
             --command COMMAND     agent command to run ['server', 'tune', 'restore',
                                   'snapshot']
             --conf CONF           where to load configuration data
             --cass-conf CASS_CONF
                                   configuration to tune cassandra
             --restore-point RESTORE_POINT
                                   The name of the file to be used as a restore point w/o
                                   .tar.gz


The available list of commands are tune, server, and restore. 
---------------------------------------------------------------
The --conf option can be used to load a different configurator::

        $ hector --command server --conf my-settings.py

The --cass-conf option can be used in conjunction with the tune command to write the cassandra.yaml to non-default location::

        $ hector --command tune --cass-conf /usr/path/cassandra.yaml
        $ ls -l /usr/path/cassandra.yaml
          -rw-rw-r--. 1 guest guest 2549 Jul  99 03:56 cassandra.yam

The restore command takes the non-optional --restore-point option.::
        
        $ hector --command restore --restore-point 1372972141943


The Restore Point should be a snapshot name, from a snapshot or backup that has been taken by the agent (i.e. ).::
        
        hector::settings::config.py.backup_dir + [restore-point] + .tar.gz
        Should exist and be a compressed tar file of a backup or snapshot keyspaces


The snapshot commmand performs the snapshot action using the current configuration in settings/config.py::

        $ hector --command snapshot


The Server command starts the Hector Agent processes.::

        $ hector --command server
