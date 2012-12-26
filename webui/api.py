from __future__ import unicode_literals

import json
from decimal import Decimal

from twisted.web.resource import Resource

from axiom.store import Store
from axiom.attributes import text, integer, point2decimal

from db import Crop

def identity(obj):
    return obj

_parser = {
    text: identity,
    integer: int,
    point2decimal: Decimal,
    }


def _parse(itemType, attributes):
    for name, serialized in attributes.iteritems():
        if name == b"id":
            continue
        structured = _parser[type(getattr(itemType, name))](serialized)
        yield name, structured


def viewify(crop):
    result = dict(crop.persistentValues())
    result[b"yield_lbs_per_bed_foot"] = str(result[b"yield_lbs_per_bed_foot"])
    result[b"id"] = crop.storeID
    return result


class CropCollection(Resource):
    @property
    def crops(self):
        return self.store.query(Crop)


    def __init__(self, store):
        Resource.__init__(self)
        self.store = store


    def getChild(self, name, request):
        return SingleCrop(self.store, int(name))


    def render_GET(self, request):
        request.responseHeaders.setRawHeaders(b"content-type", [b"text/json"])
        return json.dumps([
                viewify(crop) for crop in self.crops])


    def render_POST(self, request):
        attributes = _parse(Crop, json.loads(request.content.read()))
        crop = Crop(store=self.store, **dict(attributes))
        return json.dumps(viewify(crop))



class SingleCrop(Resource):
    def __init__(self, store, cropIdentifier):
        Resource.__init__(self)
        self.store = store
        self.cropIdentifier = cropIdentifier


    def render_PUT(self, request):
        crop = self.store.getItemByID(self.cropIdentifier)
        for name, value in _parse(Crop, json.loads(request.content.read())):
            setattr(crop, name, value)
        return json.dumps(viewify(crop))


    def render_DELETE(self, request):
        crop = self.store.getItemByID(self.cropIdentifier)
        crop.deleteFromStore()
        return b""


def api(path):
    store = Store(path)
    api = Resource()
    api.putChild(b"crops", CropCollection(store))
    return api
