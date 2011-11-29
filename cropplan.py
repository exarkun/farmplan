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
    @property
    def fresh_yield(self):
        return self.fresh_eating_weeks * self.fresh_eating_lbs


    @property
    def storage_yield(self):
        return self.storage_eating_weeks * self.storage_eating_lbs


    @property
    def total_yield(self):
        return self.fresh_yield + self.storage_yield



class Seed(record(
        'crop variety '
        'greenhouse_days beginning_of_season maturity_days end_of_season '
        'seeds_per_packet row_foot_per_packet '
        'seeds_per_oz dollars_per_packet dollars_per_row_foot_packet '
        'dollars_per_thousand dollars_per_oz '
        'dollars_per_row_foot_thousand row_foot_per_oz dollars_per_row_foot_oz '
        'dollars_per_mini seeds_per_mini row_foot_per_mini favored '
        'harvest_duration notes')):
    """
    @ivar crop: The name of the crop - matches the name of one of the L{Crop}
        instances.
    @ivar variety: The name of a specific variety or cultivar of this crop.

    @ivar greenhouse_days: The number of days to keep this variety in a
        greenhouse before transplanting outdoors.

    @ivar beginning_of_season: The first date at which this variety can be
        transplanted outdoors.  This is an integer giving a day of the year.

    @ivar maturity_days: The number of days from planting or transplanting
        outdoors until the variety can be harvested.

    @ivar end_of_season: The last date at which this variety is viable for for
        harvest outdoors.  This is an integer giving a day of the year.

    @ivar seeds_per_packet: If seeds are sold by the packet, the number of seeds
       in a packet of this variety (from a particular vendor - XXX vendor
       unspecified).  May be C{None} if seeds are not sold by the packet or if
       we didn't feel like entering that data.

    @ivar row_foot_per_packet: The number of row feet one packet of seeds will
        plant.  May be C{None} if seeds are not sold by the packet, etc.

    @ivar seeds_per_oz: Number of seeds in one ounce of seeds of this variety.
        May be C{None}, etc.

    @ivar dollars_per_packet: The price of a packet of seeds of this variety.
        May be C{None}, etc.

    @ivar dollars_per_row_foot_packet: The price to plant one row foot of this
        variety, assuming seeds are bought by the packet.  May be C{None}, etc.

    @ivar dollars_per_thousand: If seeds are sold by the 1000, the price of 1000
        seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_oz: If seeds are sold by the ounce, the price of one ounce
        of seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_row_foot_thousand: The price to plant one row foot of this
        variety, assuming seeds are bought by the 1000.  May be C{None}.

    @ivar row_foot_per_oz: The number of row feet one ounce of seed of this
        variety will plant.  May be C{None}, etc.

    @ivar dollars_per_row_foot_oz: The price to plant one row foot of this
        variety, assuming seeds are bought by the ounce.  May be C{None}, etc.

    @ivar dollars_per_mini: The cost of a mini of seeds of this variety.  May be
        C{None}.

    @ivar seeds_per_mini: The number of seeds in a mini of this variety.  May be
        C{None}.

    @ivar row_foot_per_mini: The number of row feet one mini of seed of this
        variety will plant.  May be C{None}.

    @ivar favored: Bogus, unused.

    @ivar harvest_duration: The number of days for which this variety can be
        harvested once it is mature.

    @ivar notes: Freeform text.
    """



def load_crops(path):
    data = reader(path.open())
    # Ignore the first two rows
    data.next()
    data.next()
    crops = []
    for row in data:
        crops.append(
            Crop(row[0], *[float(field or '0.0') for field in row[1:]]))
    return crops



def summarize_crops(crops):
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



def parse_or_default(parser, string, default):
    """
    Parse the given string using the given parser, or return the given default
    if the string is empty.
    """
    if string:
        return parser(string)
    return default



def parse_date(string):
    month, day, year = map(int, string.split('/'))
    # Close enough
    return month * 30 + day



def load_seeds(path):
    data = reader(path.open())
    # Ignore the first row
    data.next()
    seeds = []
    for row in data:
        seeds.append(Seed(
                crop=row[0], variety=row[1],
                greenhouse_days=parse_or_default(int, row[2], None),
                beginning_of_season=parse_or_default(parse_date, row[3], None),
                maturity_days=parse_or_default(int, row[4], None),
                end_of_season=parse_or_default(parse_date, row[5], None),
                seeds_per_packet=parse_or_default(int, row[6], None),
                row_foot_per_packet=parse_or_default(float, row[7], None),
                seeds_per_oz=parse_or_default(float, row[8], None),
                dollars_per_packet=parse_or_default(float, row[9], None),
                dollars_per_row_foot_packet=parse_or_default(float, row[10], None),
                dollars_per_thousand=parse_or_default(float, row[11], None),
                dollars_per_oz=parse_or_default(float, row[12], None),
                dollars_per_row_foot_thousand=parse_or_default(float, row[13], None),
                row_foot_per_oz=parse_or_default(float, row[14], None),
                dollars_per_row_foot_oz=parse_or_default(float, row[15], None),
                dollars_per_mini=parse_or_default(float, row[16], None),
                seeds_per_mini=parse_or_default(int, row[17], None),
                row_foot_per_mini=parse_or_default(float, row[18], None),
                favored=row[19],
                harvest_duration=parse_or_default(int, row[20], None),
                notes=row[21],
                ))
    return seeds



def summarize_seeds(crops, seeds):
    crops = dict([(crop.name, crop) for crop in crops])
    for seed in seeds:
        crop = crops[seed.crop]
        bed_feet = crop.total_yield / crop.yield_lbs_per_bed_foot
        print 'Plant', bed_feet, 'feet of', seed.variety, '(', crop.name, ')'



def main():
    crops = load_crops(FilePath(argv[1]))
    seeds = load_seeds(FilePath(argv[2]))
    summarize_crops(crops)
    summarize_seeds(crops, seeds)

if __name__ == '__main__':
    main()