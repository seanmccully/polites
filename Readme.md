Hector
======
# Installing
## A bootstrap.sh util script exists for install the needed libaries for Cassandra and hector to run.
## To install just hector, setup.py exists.
	$ python setup.py install 

# Running
## Once installed hector can be run from the command line. To get the hector server/agent up and running, use the server command.
	$ hector --command server
## To check that hector start properly, hector provides client commands
	$ hector --command client status
	<xml><status>Running</status></xml>
        <xml><auto-snapshot>True</auto-snapshot><last-snapshot>1381067808927</last-snapshot></xml>
## If there was a problem starting Cassandra Hector will attempt to read cassandra log file located in the configuration provided by config.py.
	##Cassandra HOME
	cass_home = "/var/lib/cassandra"
	default_web_port = 8080
	hostname = None
## If there was a problem starting the hector server, hector logs to hector.log in the current directory hector is being ran from.
	$ ls -l hector.log
	hector.log


# Python Agent for running alongside Cassandra provides cli options for configuration management, performing snapshots, and restoring from a snapshot/backup #
## REST API 
   * Status of Node, with Error message
   * Force Start/Restart of Node*
   * Take Snapshot*
   * Restore from File*

## Documentation ##

### After starting the hector agent server  command (# python agent.py --command server). ###
### The documentation can be viewed at http://\<hostname\>:\<port\>/docs ##
   * The default hostname in the settings/config.py is 127.0.0.1
   * The default port in settings/config.py is 8080
   * Restarting/Starting Cassandra also updates configuration
     *  Restarting/Starting Cassandra can be accomplished via curl command
     * curl -X POST -d "restart=True" http://\<host\>:\<port\>/
   * Documentation : build/html/index.html

### Install Apache Cassandra and Python Requirements File ###
   * git clone https://github.com/seanmccully/hector.git
   * cd hector
   * ./install.sh
   * Will try to install java, python, pip dependencies, and apache cassandra. Once install.sh finishes you should be able to run hector/agent.py from any directory
