import os
from twisted.web.resource import Resource
from twisted.internet import reactor
from twisted.web.error import Error

class BaseHector(Resource):
    isLeaf = True

    def __init__(self, cass):
        Resource.__init__(self)
        self.cass = cass

class Hector(BaseHector):
    running_str = "<xml><status>Running</status></xml>"
    error_str = "<xml><status>Stopped</status><error><![CDATA[%s]]></error></xml>"

    def getChild(self, name, request):
        if name == '':
            return self
        return Resource.getChild(self, name, request)

    def render_GET(self, request):
        if self.cass.cassandra_running:
            return self.running_str
        else:
            if self.cass.cass_error_msg:
                return self.error_str % self.cass.cass_error_msg

    def render_POST(self, request):
        restart = False
        if 'restart' in request.args:
            restart = request.args['restart']
            if type(restart) == list:
                restart = restart[0]
                if restart.lower() == 'true':
                    restart = True

        def do_request(start=True):
            if start:
                self.cass.safe_start_cassandra()
            if self.monitor_proc(autostart=False):
                return self.running_str
            else:
                return self.error_str % self.cass.cass_error_msg

        if not self.cass.cassandra_running or restart:
            return do_request(start=True)
        return do_request()


class SnapShot(BaseHector):

    def render_GET(self, request):
        return "<xml><auto-snapshot>%s</auto-snapshot><last-snapshot>%s</last-snapshot></xml>" %  (self.cass.config.auto_snapshot, self.cass.latest_snapshot, )


    def render_PUT(self, request):
        reactor.callLater(1, self.cass.take_snapshot)
        return "<xml><snapshot>True</snapshot></xml>"


class Restore(BaseHector):

    def render_POST(self, request):
        if 'snapshot-name' in request.args:
            snapshot_name = request.args['snapshot-name'][0]
            snapshot_location = os.path.join(self.cass.config.backup_dir, snapshot_name + '.tar.gz')
            reactor.callLater(1, self.cass.do_restore, snapshot_location)
            return "<xml><status>Success</success></xml>"
        else:
            raise Error(code=400, message="MISSING ARGS", response="<xml><error>Missing Request Arg snapshot-name</error></xml>")


class Nodes(BaseHector):

    def render_GET(self, request):
        xml_str = '<xml><nodesList>'
        seeds = self.cass.config.seeds.split(',')

