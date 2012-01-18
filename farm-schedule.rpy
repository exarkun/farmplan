
import sys

from StringIO import StringIO

from twisted.python.filepath import FilePath
from twisted.web.resource import Resource

from cropplan import load_crops, load_seeds, create_tasks, schedule_tasks

HERE = FilePath(_).realpath().parent()
CROP_PLAN = HERE.child('2012 Crop Plan.csv')
CROP_VARIETIES = HERE.child('2012 Crop Plan - Varieties.csv')


class FarmSchedule(Resource):
    def render_GET(self, request):
        crops = load_crops(CROP_PLAN)
        seeds = load_seeds(CROP_VARIETIES, crops)
        tasks = create_tasks(crops, seeds)
        schedule = schedule_tasks(tasks)

        output = StringIO()
        stdout = sys.stdout
        try:
            sys.stdout = output
            schedule_ical(schedule)
        finally:
            sys.stdout = stdout
        request.responseHeaders.setRawHeader('content-type', ['text/calendar'])
        return output.getvalue()

resource = FarmSchedule()
