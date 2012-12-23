from twisted.python.filepath import FilePath
from twisted.web.static import File
from api import api

resource = File(".")
resource.putChild("api", api(FilePath(__file__).sibling("crops.axiom")))
