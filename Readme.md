Polites
======
# Installing
## A bootstrap.sh util script exists for install the needed libaries for Cassandra and polites to run.
## To install just polites, setup.py exists.
	$ python setup.py install 

# Running
## Once installed polites can be run from the command line. To get the polites server/agent up and running, use the server command.
	$ polites --command server
## To check that polites start properly, polites provides client commands
	$ polites --command client status
	<xml><status>Running</status></xml>
        <xml><auto-snapshot>True</auto-snapshot><last-snapshot>1381067808927</last-snapshot></xml>
## If there was a problem starting Cassandra Polites will attempt to read cassandra log file located in the configuration provided by config.py.
	##Cassandra HOME
	cass_home = "/var/lib/cassandra"
	default_web_port = 8080
	hostname = None
## If there was a problem starting the polites server, polites logs to polites.log in the current directory polites is being ran from.
	$ ls -l polites.log
	polites.log


# Python Agent for running alongside Cassandra provides cli options for configuration management, performing snapshots, and restoring from a snapshot/backup #
## REST API 
   * Status of Node, with Error message
   * Force Start/Restart of Node*
   * Take Snapshot*
   * Restore from File*

## Documentation ##

### After starting the polites agent server  command (# python agent.py --command server). ###
### The documentation can be viewed at http://\<hostname\>:\<port\>/docs ##
   * The default hostname in the settings/config.py is 127.0.0.1
   * The default port in settings/config.py is 8080
   * Restarting/Starting Cassandra also updates configuration
     *  Restarting/Starting Cassandra can be accomplished via curl command
     * curl -X POST -d "restart=True" http://\<host\>:\<port\>/
   * Documentation : build/html/index.html

### Install Apache Cassandra and Python Requirements File ###
   * git clone https://github.com/seanmccully/polites.git
   * cd polites
   * ./install.sh
   * Will try to install java, python, pip dependencies, and apache cassandra. Once install.sh finishes you should be able to run polites/agent.py from any directory
