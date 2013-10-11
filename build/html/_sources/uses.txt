How to Use Polites From the Command Line
=======================================

Using Polites from the Command Line::

        $ polites --help
           optional arguments:
             -h, --help            show this help message and exit
             --command COMMAND     agent command to run ['server', 'tune', 'restore',
                                   'snapshot', 'client']
             --conf CONF           where to load configuration data
             --cass-conf CASS_CONF
                                   configuration to tune cassandra
             --restore-point RESTORE_POINT
                                   The name of the file to be used as a restore point w/o
                                   .tar.gz


The available list of commands are tune, server, and restore. 
---------------------------------------------------------------
The --conf option can be used to load a different configurator::

        $ polites --command server --conf my-settings.py

The --cass-conf option can be used in conjunction with the tune command to write the cassandra.yaml to non-default location::

        $ polites --command tune --cass-conf /usr/path/cassandra.yaml
        $ ls -l /usr/path/cassandra.yaml
          -rw-rw-r--. 1 guest guest 2549 Jul  99 03:56 cassandra.yam

The restore command takes the non-optional --restore-point option.::
        
        $ polites --command restore --restore-point 1372972141943


The Restore Point should be a snapshot name, from a snapshot or backup that has been taken by the agent (i.e. ).::
        
        polites::settings::config.py.backup_dir + [restore-point] + .tar.gz
        Should exist and be a compressed tar file of a backup or snapshot keyspaces


The snapshot commmand performs the snapshot action using the current configuration in settings/config.py::

        $ polites --command snapshot


The Server command starts the Polites Agent processes.::

        $ polites --command server

The Client Command Allows for making HTTP Commands to the configured polites server. If the supplementary command to client is supplied, the default status command is used. Restore uses the last-snapshot result.::

        $ polites --command client ['status', 'restart', 'snapshot', 'restore']
        <xml><status>Running</status></xml>
        <xml><auto-snapshot>True</auto-snapshot><last-snapshot>1381067808927</last-snapshot></xml>



:doc:`contact`
