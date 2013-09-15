Hector
======
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
