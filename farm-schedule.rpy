
import sys

from StringIO import StringIO

from twisted.python.filepath import FilePath
from twisted.web.resource import Resource

from cropplan import main

HERE = FilePath(__file__)
CROP_PLAN = HERE.sibling('2012 Crop Plan.csv')
CROP_VARIETIES = HERE.sibling('2012 Crop Plan - Varieties.csv')


class FarmSchedule(Resource):
    def render_GET(self, request):
        output = StringIO()
        stdout = sys.stdout
        try:
            sys.stdout = output
            main(['--schedule', 'ical', CROP_PLAN.path, CROP_VARIETIES.path])
        finally:
            sys.stdout = stdout
        request.setHeader('content-type', 'text/calendar')
        return output.getvalue()

resource = FarmSchedule()
