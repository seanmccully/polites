Example setting up a Cassandra Cluster
=======================================


Setting Up a 3 Node Cassandra Cluster
---------------------------------------------------------------
The easiest way to use polites is to use the bootstrap script. Which installs the python dependencies and cassandra to path that polites uses as the config defaults. But this can easily be changed by
modifying the config settings.::

        $ git clone https://github.com/seanmccully/polites.git
        Initialized empty Git repository in /home/smccully/polites/.git/
        remote: Counting objects: 342, done.
        remote: Compressing objects: 100% (238/238), done.
        remote: Total 342 (delta 199), reused 234 (delta 93)
        Receiving objects: 100% (342/342), 260.50 KiB, done.
        Resolving deltas: 100% (199/199), done.


        $ cd polites/
        $ ./bootstrap.sh 
        which: no java in (/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/home/smccully/bin)
        which: no 2 in (/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/home/smccully/bin)
        which: no 2 in (/usr/local/bin:/bin:/usr/bin:/usr/local/sbin:/usr/sbin:/sbin:/home/smccully/bin)
        Loaded plugins: fastestmirror
        Determining fastest mirrors
         * base: centosz4.centos.org
         * extras: centosb5.centos.org
         * updates: centosi5.centos.org
        Setting up Install Process
        .....
        ....

Optionally you can install just polites and the python dependencies::

        $ cd polites/
        $ python setup.py install

Once the install script has finished, can run from /usr/bin/polites.py::

        $ polites --command server


When ready to start additional nodes in the cluster, will need to make a few modifications to the configuration. Open /usr/etc/polites/config.py in your favorite editor.::

        $ vi /usr/etc/polites/config.py

                seeds = '192.168.1.93' # Set this to the first cassandra node you started
                cluster_num = 1 # Set this to the number which node represents in the ring
                num_nodes = 3 # Here we set the number to total number of nodes we plan on using

        $ polites.py --command server

Finally we can check that cassandra is running on all hosts.::

        $ curl http://192.168.1.93:8080
        <xml><status>Running</status></xml>


        $ curl http://192.168.1.94:8080
        <xml><status>Running</status></xml>

        $ curl http://192.168.1.95:8080
        <xml><status>Running</status></xml>

Finally We should be able to check that all nodes belong to the same ring.::


        $ /var/lib/cassandra/bin/nodetool ring
        Note: Ownership information does not include topology; for complete information, specify a keyspace
        
        Datacenter: datacenter1
        ==========
        Address       Rack        Status State   Load            Owns                Token
                                                                                     3074457345618258602
        192.168.1.93  rack1       Up     Normal  74.76 KB        33.33%              -6148914691239313638
        192.168.1.93  rack1       Up     Normal  74.76 KB        33.33%              -6148914691237216715
        192.168.1.93  rack1       Up     Normal  74.76 KB        33.33%              0
        192.168.1.95  rack1       Up     Normal  69.98 KB        50.00%              -6148914691236517547
        192.168.1.95  rack1       Up     Normal  69.98 KB        50.00%              -683
        192.168.1.95  rack1       Up     Normal  69.98 KB        50.00%              6148914691236517205
        192.168.1.94  rack1       Up     Normal  38.4 KB         16.67%              1024819115206086126
        192.168.1.94  rack1       Up     Normal  38.4 KB         16.67%              2049638230412172279
        192.168.1.94  rack1       Up     Normal  38.4 KB         16.67%              3074457345618258602
        



Troubleshooting
-----------------

Polites Will try to provide the latest error from the cassandra log file. There isn't always an error in the log file if cassandra fails to start.
In these cases polites just prints a general error message.::

        $ curl http://192.168.1.95:8080
        <xml><status>Stopped</status><error><![CDATA[possible configuration error]]></error></xml>

        


        $ curl http://192.168.1.95:8080
        <xml><status>Stopped</status><error><![CDATA[ERROR [main] 2013-09-08 23:44:47,137 DatabaseDescriptor.java (line 503) Fatal configuration error
        at org.apache.cassandra.dht.Murmur3Partitioner$1.validate(Murmur3Partitioner.java:182)
        at org.apache.cassandra.config.DatabaseDescriptor.loadYaml(DatabaseDescriptor.java:443)
        at org.apache.cassandra.config.DatabaseDescriptor.<clinit>(DatabaseDescriptor.java:123)
        at org.apache.cassandra.service.CassandraDaemon.setup(CassandraDaemon.java:217)
        at org.apache.cassandra.service.CassandraDaemon.activate(CassandraDaemon.java:447)
        at org.apache.cassandra.service.CassandraDaemon.main(CassandraDaemon.java:490)


:doc:`contact`
