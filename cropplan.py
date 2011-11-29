from csv import reader
from sys import argv

from twisted.python.filepath import FilePath

from epsilon.structlike import record


class Crop(record(
        'name '
        'fresh_eating_lbs fresh_eating_weeks '
        'storage_eating_lbs storage_eating_weeks '
        'variety harvest_weeks row_feet_per_oz_seed '
        'yield_lbs_per_bed_foot bed_feet')):
    """
    @ivar name: The general name of this crop (eg carrots, beets)

    @ivar fresh_eating_lbs: Number of pounds of this crop per week to be eaten
        fresh (ie, unpreserved)
    @ivar fresh_eating_weeks: Number of weeks to eat this crop fresh

    @ivar storage_eating_lbs: Number of pounds of this crop per week to be eaten
        from storage (canned, pickled, root cellar, etc) after the season ends.
    @ivar storage_eating_weeks: Number of weeks to eat this crop from storage

    @ivar variety: Bogus, ignore

    @ivar harvest_weeks: Number of weeks of to be harvesting one planting of
        this crop.

    @ivar row_feet_per_oz_seed: Bogus, ignore

    @ivar yield_lbs_per_bed_foot: Number of pounds of this crop produced per bed
        foot (three foot wide bed) planted.

    @ivar bed_feet: Number of bed feet to plant in this crop.
    """


def parse_field(parser, string, default):
    """
    Parse the given string using the given parser, or return the given default
    if the string is empty.
    """
    if string:
        return parser(string)
    return default


def main():
    data = reader(FilePath(argv[1]).open())
    # Ignore the first two rows
    data.next()
    data.next()
    crops = []
    for row in data:
        crops.append(
            Crop(row[0], *[float(field or '0.0') for field in row[1:]]))
    for crop in crops:
        print crop.name, ':'
        print '\tBed feet', crop.bed_feet
        print '\tFresh pounds', crop.fresh_eating_weeks * crop.fresh_eating_lbs
        print '\tStorage pounds', crop.storage_eating_weeks * crop.storage_eating_lbs

    print 'Total crops:', len(crops)
    print 'Total feet:', sum([crop.bed_feet for crop in crops])
    print 'Fresh pounds:', sum([
            crop.fresh_eating_weeks * crop.fresh_eating_lbs for crop in crops])
    print 'Storage pounds:', sum([
            crop.storage_eating_weeks * crop.storage_eating_lbs
            for crop in crops])

if __name__ == '__main__':
    main()
