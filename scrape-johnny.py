
from urllib import quote
from sys import stdout, argv

from twisted.python.filepath import FilePath
from twisted.python.log import startLogging, err
from twisted.web.client import getPage
from twisted.internet import reactor
from twisted.internet.task import cooperate
from twisted.internet.defer import Deferred, gatherResults

from html5lib import parse

from cropplan import load_crops, load_seeds

class TimeoutError(Exception):
    pass

SEARCH = "http://www.johnnyseeds.com/search.aspx?SearchTerm=%s"

def getPageWithTimeout(url):
    finished = [False]
    d = getPage(url)
    result = Deferred()

    def timeout():
        if not finished[0]:
            finished[0] = True
            result.errback(TimeoutError())
    reactor.callLater(45, timeout)

    def done(passthrough):
        if not finished[0]:
            finished[0] = True
            result.callback(passthrough)
    d.addBoth(done)

    return result


def search(crop, variety):
    print 'Searching for', crop, variety
    d = getPageWithTimeout(SEARCH % (quote("%s %s" % (crop, variety), safe="")),)
    def got(page):
        print 'Got a page, parsing'
        document = parse(page, treebuilder='lxml')
        links = document.xpath('//html:a[@class="more_details_link"]',namespaces={'html': 'http://www.w3.org/1999/xhtml'})
        results = []
        for a in links:
            next = a.getnext()
            if next is not None:
                results.append((a.text, next.text))
        return results
    d.addCallback(got)
    return d


class Collector(object):
    def __init__(self):
        self.results = []


    def search(self, seed):
        d = search(seed.crop.name, seed.variety)
        d.addCallback(self.collect, seed)
        d.addErrback(self.retry, seed)
        return d


    def retry(self, reason, seed):
        err(reason, "Searching for %s failed, retrying" % (seed.variety,))
        return self.search(seed)


    def collect(self, results, seed):
        self.results.append((seed, results))


def main():
    startLogging(stdout, False)
    crops = load_crops(FilePath(argv[1]))
    seeds = load_seeds(FilePath(argv[2]), crops)

    collector = Collector()
    work = (collector.search(seed) for seed in seeds)

    tasks = [cooperate(work), cooperate(work)]
    d = gatherResults([task.whenDone() for task in tasks])
    d.addErrback(err)
    def done(ignored):
        reactor.stop()
    d.addCallback(done)
    reactor.run()

    selected = []
    for seed, results in collector.results:
        print 'Select result for', seed.crop.name, seed.variety
        for i, (text, identifier) in enumerate(results, 1):
            print i, '-', text
        print i + 1, '- None of the above'
        selection = int(raw_input("> "))
        if selection == i + 1:
            productID = "None"
        else:
            productID = results[selection - 1][1]
        selected.append((seed, productID))

    selected.sort(key=lambda (seed, productID): seeds.index(seed))
    for seed, productID in selected:
        print '%s,%s,%s' % (seed.crop.name, seed.variety, productID.replace("Product ID: ", ""))


if __name__ == '__main__':
    main()
