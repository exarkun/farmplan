from __future__ import unicode_literals

import json

from twisted.web.resource import Resource

from axiom.store import Store

from db import Crop

def viewify(crop):
    return dict(name=crop.name, id=crop.storeID, picture=None, description=crop.description)


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
        attributes = json.loads(request.content.read())
        del attributes['id']
        crop = Crop(store=self.store, **attributes)
        return json.dumps(viewify(crop))


class SingleCrop(Resource):
    def __init__(self, store, cropIdentifier):
        Resource.__init__(self)
        self.store = store
        self.cropIdentifier = cropIdentifier


    def render_PUT(self, request):
        attributes = json.loads(request.content.read())
        del attributes['id']
        crop = self.store.getItemByID(self.cropIdentifier)
        for k, v in attributes.iteritems():
            setattr(crop, k, v)
        return json.dumps(viewify(crop))


def api(path):
    store = Store(path)
    api = Resource()
    api.putChild(b"crops", CropCollection(store))
    return api
