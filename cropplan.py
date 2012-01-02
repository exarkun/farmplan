from csv import reader
from sys import argv
from math import ceil
from itertools import groupby
from datetime import date, datetime, timedelta

from dateutil.rrule import SU

from vobject import iCalendar

from twisted.python.filepath import FilePath
from twisted.python.usage import Options

from epsilon.structlike import record

YEAR = 2012

def make_coercer(valid):
    def coerce(value):
        try:
            return valid[value]
        except KeyError:
            raise ValueError("%r is not valid; try one of %s" % (
                    value, ", ".join(valid)))
    return coerce



def display_nothing(*args, **kwargs):
    pass



def schedule_plaintext(schedule):
    for event in schedule:
        print '%(event)s on %(date)s' % dict(
            event=event.summarize(), date=event.when)



def schedule_ical(schedule):
    cal = iCalendar()
    for event in schedule:
        vevent = cal.add('vevent')
        vevent.add('dtstart').value = event.when
        vevent.add('dtend').value = event.when + event.duration

        vevent.add('summary').value = event.summarize()
    print cal.serialize()



def summarize_crops(crops):
    for crop in crops.itervalues():
        print crop.name, ':'
        print '\tBed feet', crop.bed_feet
        print '\tFresh pounds', crop.fresh_eating_weeks * crop.fresh_eating_lbs
        print '\tStorage pounds', crop.storage_eating_weeks * crop.storage_eating_lbs

    print 'Total crops:', len(crops)
    print 'Total feet:', sum([crop.bed_feet for crop in crops.itervalues()])
    print 'Fresh pounds:', sum([
            crop.fresh_eating_weeks * crop.fresh_eating_lbs for crop in crops.itervalues()])
    print 'Storage pounds:', sum([
            crop.storage_eating_weeks * crop.storage_eating_lbs
            for crop in crops.itervalues()])



def summarize_crops_graph(crops):
    import matplotlib.pyplot as plt
    # A figure - whatever that is
    fig = plt.figure()

    # A subplot - whatever that is.  The three arguments define the grid
    # parameters.  The first is the number of rows per unit; the second is the
    # number of columns per unit; the last is uniquely identifies the plot being
    # operated on.
    plot = fig.add_subplot(1, 1, 1)

    # x values
    indices = range(len(crops))
    # width of each bar in an unknown unit
    width = 0.9

    cropdata = sorted(crops.items())

    fresh_yields = [crop.fresh_yield for (name, crop) in cropdata]
    storage_yields = [crop.storage_yield for (name, crop) in cropdata]

    fresh_bar = plot.bar(
        indices, fresh_yields, width, color='g')
    storage_bar = plot.bar(
        indices, storage_yields, width, color='brown', bottom=fresh_yields)

    plot.set_title('Expected Yields')
    plot.set_ylabel('Pounds')
    plot.legend((fresh_bar[0], storage_bar[0]), ('Fresh', 'Storage'))

    # Positions of the ticks
    plot.set_xticks([i + width / 2 for i in indices])

    # Labels for the ticks
    labels = plot.set_xticklabels([
            '\n'.join(name.split(None, 1)) for (name, crop) in cropdata])

    # Get the xticks to not overlap each other
    labels = plot.get_xticklabels()
    for label in labels:
        label.update(dict(rotation='vertical'))

    plt.show()



def summarize_order(order):
    for item in order:
        print '%(variety)s (%(crop)s) $%(cost)5.2f' % dict(
            variety=item.seed.variety, crop=item.seed.crop.name,
            cost=item.cost() / item.seed.crop.total_yield)



def summarize_seedlings(schedule):
    flats = 0
    for event in schedule:
        if isinstance(event, (SeedFlats, Transplant)):
            flats += event.required_flats()
            print 'After', event, 'in use flats is', flats



def summarize_seedlings_graph(schedule):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    dates = [date(YEAR, 1, 1)]
    flats = [0]
    for event in schedule:
        if isinstance(event, (SeedFlats, Transplant)):
            dates.append(event.when)
            flats.append(flats[-1] + event.required_flats())

    months = mdates.MonthLocator()
    days = mdates.WeekdayLocator(byweekday=SU)
    monthsFmt = mdates.DateFormatter('%b')

    fig = plt.figure()

    plot = fig.add_subplot(1, 1, 1)

    plot.set_title('Flat Usage')
    plot.set_ylabel('72 Cell Flats In Use')

    plot.plot(dates, flats)

    plot.xaxis.set_major_locator(months)
    plot.xaxis.set_major_formatter(monthsFmt)
    plot.xaxis.set_minor_locator(days)

    plot.format_xdata = mdates.DateFormatter('%Y-%m-%d')

    # Do this after other stuff, because this shit is all about side-effects.
    fig.autofmt_xdate()

    plt.show()


class CropPlanOptions(Options):
    optParameters = [
        ('schedule', None, None,
         'Summarize the labor schedule (text or ical).',
         make_coercer(dict(text=schedule_plaintext, ical=schedule_ical))),
        ('crops', None, None,
         'Summarize the crops being planted (text or graph).',
         make_coercer(dict(text=summarize_crops, graph=summarize_crops_graph))),
        ('order', None, None,
         'Summarize the seed order (text or graph).',
         make_coercer(dict(text=summarize_order))),
        ('flats', None, None, 'Summarize flats usage.',
         make_coercer(dict(text=summarize_seedlings, graph=summarize_seedlings_graph))),
        ]

    optFlags = [
        ('beds', None, 'Summarize beds usage.'),
        ('yields', None, 'Summarize yield.'),
        ]

    def __init__(self):
        Options.__init__(self)
        self['schedule'] = display_nothing
        self['crops'] = display_nothing
        self['seeds'] = display_nothing
        self['order'] = display_nothing


    def parseArgs(self, crop, seed):
        self['crop-path'] = FilePath(crop)
        self['seed-path'] = FilePath(seed)



class MissingInformation(object):
    def __init__(self, message):
        self.message = message



class Crop(record(
        'name '
        'fresh_eating_lbs fresh_eating_weeks '
        'storage_eating_lbs storage_eating_weeks '
        'variety harvest_weeks row_feet_per_oz_seed '
        'yield_lbs_per_bed_foot rows_per_bed in_row_spacing _bed_feet')):
    """
    @ivar name: The general name of this crop (eg carrots, beets)

    @ivar fresh_eating_lbs: Number of pounds of this crop per week to be eaten
        fresh (ie, unpreserved)
    @ivar fresh_eating_weeks: Number of weeks to eat this crop fresh

    @ivar storage_eating_lbs: Number of pounds of this crop per week to be eaten
        from storage (canned, pickled, root cellar, etc) after the season ends.
    @ivar storage_eating_weeks: Number of weeks to eat this crop from storage

    @ivar variety: Bogus, ignore

    @ivar varieties: A C{list} of L{Seed} instances representing the specific
        varieties of this crop for which data is available.

    @ivar harvest_weeks: Number of weeks of to be harvesting one planting of
        this crop.

    @ivar row_feet_per_oz_seed: Bogus, ignore

    @ivar rows_per_bed: The number of rows of this seed sewn per bed.  XXX
        Missing from the underlying data, add it.

    @ivar yield_lbs_per_bed_foot: Number of pounds of this crop produced per bed
        foot (three foot wide bed) planted.

    @ivar in_row_spacing: Spacing between within each row in a bed of this crop
        (feet).

    @ivar _bed_feet: Number of bed feet to plant in this crop.
    """
    def __init__(self, *args, **kwargs):
        super(Crop, self).__init__(*args, **kwargs)
        self.varieties = []


    @property
    def bed_feet(self):
        if self.total_yield and self.yield_lbs_per_bed_foot:
            return self.total_yield / self.yield_lbs_per_bed_foot
        if self._bed_feet is not None:
            return self._bed_feet
        raise RuntimeError("Who knows? %r" % (self,))


    @property
    def fresh_yield(self):
        return self.fresh_eating_weeks * self.fresh_eating_lbs


    @property
    def storage_yield(self):
        return self.storage_eating_weeks * self.storage_eating_lbs


    @property
    def total_yield(self):
        return self.fresh_yield + self.storage_yield



class Price(record('kind dollars row_foot_increment')):
    @property
    def dollars_per_row_foot(self):
        return self.dollars / self.row_foot_increment


    def units_for(self, row_feet):
        return ceil(row_feet / self.row_foot_increment)


class _AttributeMultiple(object):
    def __init__(self, attribute_name, multiplier):
        self.attribute_name = attribute_name
        self.multiplier = multiplier


    def __get__(self, oself, type):
        value = getattr(oself, self.attribute_name)
        if value is None:
            return None
        return value * self.multiplier


class _PriceComputer(object):
    def __init__(self, kind, dollars_attribute, row_foot_attribute, seed_count_attribute, seed_count):
        self.kind = kind
        self.dollars_attribute = dollars_attribute
        self.row_foot_attribute = row_foot_attribute
        self.seed_count_attribute = seed_count_attribute
        self.seed_count = seed_count


    def __get__(self, oself, type):
        cost = getattr(oself, self.dollars_attribute)
        if self.seed_count is None:
            count = getattr(oself, self.seed_count_attribute)
        else:
            count = self.seed_count

        if self.row_foot_attribute is None and count is not None:
            feet = oself._count_to_feet(count)
        elif self.row_foot_attribute is not None:
            feet = getattr(oself, self.row_foot_attribute)
        else:
            feet = None

        if cost is None or count is None or feet is None:
            return None

        return Price(
            kind=self.kind,
            dollars=cost,
            row_foot_increment=feet)



class Seed(record(
        'crop variety greenhouse_days beginning_of_season maturity_days '
        'end_of_season seeds_per_packet row_foot_per_packet seeds_per_oz '
        'dollars_per_packet dollars_per_hundred dollars_per_two_fifty '
        'dollars_per_five_hundred dollars_per_thousand '
        'dollars_per_thousand_min_five dollars_per_quarter_oz '
        'dollars_per_half_oz dollars_per_oz dollars_per_eighth_lb dollars_per_quarter_lb '
        'dollars_per_half_lb dollars_per_lb row_foot_per_oz dollars_per_mini '
        'seeds_per_mini row_foot_per_mini harvest_duration notes')):
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

    @ivar dollars_per_hundred: If seeds are sold by the 100, the price of 100
        seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_two_fifty: If seeds are sold by the 250, the price of 250
        seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_five_hundred: If seeds are sold by the 500, the price of 500
        seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_thousand: If seeds are sold by the 1000, the price of 1000
        seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_thousand_min_five: If seeds are sold by the 1000 and the
        price changes when at least 5000 are ordered, the price of 1000 when
        buying at least 5000 seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_quarter_oz: If seeds are sold by the quarter ounce, the
        price of one quarter ounce of seeds of this variety.  May be C{None},
        etc.

    @ivar dollars_per_half_oz: If seeds are sold by the half ounce, the price of
        one half ounce of seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_oz: If seeds are sold by the ounce, the price of one ounce
        of seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_eighth_lb: If seeds are sold by the eighth pound, the
        price of one eighth pound of seeds of this variety.  May be C{None},
        etc.

    @ivar dollars_per_quarter_lb: If seeds are sold by the quarter pound, the
        price of one quarter pound of seeds of this variety.  May be C{None},
        etc.

    @ivar dollars_per_half_lb: If seeds are sold by the half pound, the price of
        one half pound of seeds of this variety.  May be C{None}, etc.

    @ivar dollars_per_lb: If seeds are sold by the ounce, the price of one ounce
        of seeds of this variety.  May be C{None}, etc.

    @ivar row_foot_per_oz: The number of row feet one ounce of seed of this
        variety will plant.  May be C{None}, etc.

    @ivar dollars_per_mini: The cost of a mini of seeds of this variety.  May be
        C{None}.

    @ivar seeds_per_mini: The number of seeds in a mini of this variety.  May be
        C{None}.

    @ivar row_foot_per_mini: The number of row feet one mini of seed of this
        variety will plant.  May be C{None}.

    @ivar harvest_duration: The number of days for which this variety can be
        harvested once it is mature.

    @ivar notes: Freeform text.
    """
    def _count_to_feet(self, count):
        if self.row_foot_per_thousand is None:
            return None
        return self.row_foot_per_thousand  * (count / 1000.0)


    @property
    def row_foot_per_thousand(self):
        # Assume that seeds from a packet plant the same as seeds from an M -
        # also assume that seeds are available by the M, which not all are.
        # XXX Add availability by the M to the underlying data.
        if self.seeds_per_packet is not None and self.row_foot_per_packet is not None:
            row_foot_per_seed = self.row_foot_per_packet / self.seeds_per_packet
            return row_foot_per_seed * 1000
        if self.seeds_per_oz is not None and self.row_foot_per_oz is not None:
            row_foot_per_seed = self.row_foot_per_oz / self.seeds_per_oz
            return row_foot_per_seed * 1000
        return None

    price_per_mini = _PriceComputer('mini', 'dollars_per_mini', 'row_foot_per_mini', 'seeds_per_mini', None)
    price_per_packet = _PriceComputer('packet', 'dollars_per_packet', 'row_foot_per_packet', 'seeds_per_packet', None)

    price_per_hundred = _PriceComputer('hundred', 'dollars_per_hundred', None, None, 100)
    price_per_two_fifty = _PriceComputer('two hundred fifty', 'dollars_per_two_fifty', None, None, 250)
    price_per_five_hundred = _PriceComputer('five hundred', 'dollars_per_five_hundred', None, None, 500)
    price_per_thousand = _PriceComputer('thousand', 'dollars_per_thousand', None, None, 1000)

    seeds_per_quarter_oz = _AttributeMultiple('seeds_per_oz', 0.25)
    seeds_per_half_oz = _AttributeMultiple('seeds_per_oz', 0.5)

    price_per_quarter_oz = _PriceComputer('1/4 oz', 'dollars_per_quarter_oz', None, 'seeds_per_quarter_oz', None)
    price_per_half_oz = _PriceComputer('1/2 oz', 'dollars_per_half_oz', None, 'seeds_per_half_oz', None)
    price_per_oz = _PriceComputer('ounce', 'dollars_per_oz', None, 'seeds_per_oz', None)

    seeds_per_eighth_lb = _AttributeMultiple('seeds_per_oz', 2.0)
    seeds_per_quarter_lb = _AttributeMultiple('seeds_per_oz', 4.0)
    seeds_per_half_lb = _AttributeMultiple('seeds_per_oz', 8.0)
    seeds_per_lb = _AttributeMultiple('seeds_per_oz', 16.0)

    price_per_eighth_lb = _PriceComputer('1/8 lb', 'dollars_per_eighth_lb', None, 'seeds_per_eighth_lb', None)
    price_per_quarter_lb = _PriceComputer('1/4 lb', 'dollars_per_quarter_lb', None, 'seeds_per_quarter_lb', None)
    price_per_half_lb = _PriceComputer('1/2 lb', 'dollars_per_half_lb', None, 'seeds_per_half_lb', None)
    price_per_lb = _PriceComputer('pound', 'dollars_per_lb', None, 'seeds_per_lb', None)

    @property
    def prices(self):
        price_attributes = [attr for attr in dir(self) if attr.startswith('price_')]
        prices = [getattr(self, attr) for attr in price_attributes]
        actual = filter(None, prices)
        return actual


    def order(self, bed_feet):
        prices = self.prices
        if not prices:
            return MissingInformation("Prices for %s/%s unavailable" % (
                    self.crop.name, self.variety))

        minimum_row_feet = self.crop.rows_per_bed * bed_feet

        # Put prices for all products with known row foot coverage first, since
        # we can figure out more about those.  After that, sort by cost.
        def key(price):
            return (
                not price.row_foot_increment,
                price.dollars * price.units_for(minimum_row_feet))

        prices.sort(key=key)
        price = prices[0]
        if not price.row_foot_increment:
            return MissingInformation(
                "Row foot increment for %s of %s/%s unavailable" % (
                    price.kind, self.crop.name, self.variety))

        return Order(self, minimum_row_feet, price)


    @property
    def bed_feet(self):
        """
        The number of bed feet of this variety of this crop to plant.  This is
        determined by looking at the total bed feet for the crop and dividing it
        up amongst all of the varieties being planted.
        """
        # Just divide evenly for now - change to use weights soon
        return float(self.crop.bed_feet) / len(self.crop.varieties)



def load_crops(path):
    data = reader(path.open())
    # Ignore the first two rows
    data.next()
    data.next()
    crops = {}
    for row in data:
        crop = Crop(row[0], *[float(field or '0.0') for field in row[1:]])
        crops[crop.name] = crop
    return crops



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
    # The year in the data is irrelevant garbage.  This data is cyclic with a
    # periodicity of 1 year.  If you want to plan perennials you have some work
    # cut out for you.
    when = date(YEAR, month, day)
    return int(when.strftime('%j')) - 1



def load_seeds(path, crops):
    data = reader(path.open())
    # Ignore the first row
    data.next()
    seeds = []
    for row in data:
        if not row[0]:
            continue
        crop = crops[row[0]]
        seed = Seed(
            crop=crop, variety=row[1],
            greenhouse_days=parse_or_default(int, row[2], None),
            beginning_of_season=parse_or_default(parse_date, row[3], None),
            maturity_days=parse_or_default(int, row[4], None),
            end_of_season=parse_or_default(parse_date, row[5], None),
            seeds_per_packet=parse_or_default(int, row[6], None),
            row_foot_per_packet=parse_or_default(float, row[7], None),
            seeds_per_oz=parse_or_default(float, row[8], None),
            dollars_per_packet=parse_or_default(float, row[9], None),
            dollars_per_hundred=parse_or_default(float, row[10], None),
            dollars_per_two_fifty=parse_or_default(float, row[11], None),
            dollars_per_five_hundred=parse_or_default(float, row[12], None),
            dollars_per_thousand=parse_or_default(float, row[13], None),
            dollars_per_thousand_min_five=parse_or_default(float, row[14], None),
            dollars_per_quarter_oz=parse_or_default(float, row[15], None),
            dollars_per_half_oz=parse_or_default(float, row[16], None),
            dollars_per_oz=parse_or_default(float, row[17], None),
            dollars_per_eighth_lb=parse_or_default(float, row[18], None),
            dollars_per_quarter_lb=parse_or_default(float, row[19], None),
            dollars_per_half_lb=parse_or_default(float, row[20], None),
            dollars_per_lb=parse_or_default(float, row[21], None),
            row_foot_per_oz=parse_or_default(float, row[22], None),
            dollars_per_mini=parse_or_default(float, row[23], None),
            seeds_per_mini=parse_or_default(int, row[24], None),
            row_foot_per_mini=parse_or_default(float, row[25], None),
            harvest_duration=parse_or_default(int, row[26], None),
            notes=row[27],
            )
        seeds.append(seed)
        crop.varieties.append(seed)
    return seeds



class Order(record('seed row_feet price')):
    """
    @ivar row_feet: The number of row feet of planting this order is intended to
        satisfy.  Note that the order may be for more seeds than are needed to
        plant this area.
    """
    @property
    def count(self):
        return self.price.units_for(self.row_feet)


    def excess(self):
        """
        The ratio of the number of bed feet this order will plant to the number
        of bed feet of this seed the plan calls for.
        """
        plantable_row_feet = self.count * self.price.row_foot_increment
        return plantable_row_feet / self.row_feet


    def cost(self):
        return self.price.dollars * self.count



def make_order(crops, seeds):
    key = lambda seed: seed.crop
    for (crop, varieties) in groupby(sorted(seeds, key=key), key):
        if not crop.total_yield:
            continue
        for seed in varieties:
            order = seed.order(seed.bed_feet)
            if isinstance(order, MissingInformation):
                print order.message
            else:
                yield order


def generate_seed_order(crops, seeds):
    order = list(make_order(crops, seeds))

    order_total = 0.0
    ideal_total = 0.0

    for item in order:

        cost = item.cost()
        order_total += cost
        ideal_total += cost / item.excess()

        bed_feet = item.row_feet / item.seed.crop.rows_per_bed
        print (
            'Plant %(bed_feet)s feet of %(variety)s (%(crop)s) '
            'at $%(cost)5.2f (ideally %(ideal)5.2f; %(buy)5.2f%%)' % {
                'bed_feet': bed_feet, 'variety': item.seed.variety,
                'crop': item.seed.crop.name, 'cost': cost,
                'ideal': cost / item.excess(), 'buy': item.excess() * 100})

    for item in order:
        print '\t$%(cost)5.2f %(count)d %(kind)s of %(variety)s (%(crop)s)' % dict(
            cost=item.cost(), count=item.count, kind=item.price.kind,
            variety=item.seed.variety, crop=item.seed.crop.name)
    print 'Total\t$%(cost)5.2f (ideal $%(ideal)5.2f)' % dict(
        cost=order_total, ideal=ideal_total)
    return order



class _ByTheFootTask(object):
    @property
    def duration(self):
        # Cannot multiply timedelta and float; so round up to the next integer
        # number of bed feet.  It's close enough for scheduling considerations.
        return self._time_cost * int(ceil(self.quantity))



class _DayTask(object):
    @property
    def date(self):
        return self.when.date()


class _Pretty(object):
    def __str__(self):
        return '(%s)' % (self.summarize(),)


# record needs better support for inheritance
class FinishPlanning(record('seed'), _DayTask, _Pretty):
    # Get this to sort first
    when = datetime(YEAR, 1, 1, 0, 0, 0)

    # Amount of time an event of this type takes to complete
    duration = timedelta(minutes=30)

    def summarize(self):
        return 'Finish planning %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, crop=self.seed.crop.name)



class _FlatsTask(object):
    def required_flats(self):
        crop = self.seed.crop
        seedlings = self.quantity / (crop.in_row_spacing / 12.0) * crop.rows_per_bed
        return ceil(seedlings / 72.0) * self.use_or_disuse



class SeedFlats(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, _FlatsTask):
    # Time cost in seconds for seeding one bed foot into a flat
    # XXX Should be based on what's being seeded due to spacing differences
    _time_cost = timedelta(minutes=2)

    use_or_disuse = 1

    def summarize(self):
        return 'Seed flats for %(quantity)d bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class DirectSeed(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty):
    # Time cost for direct seeding one bed foot
    # XXX I totally made this up
    _time_cost = timedelta(seconds=30)

    def summarize(self):
        return 'Direct seed %(quantity)d bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class BedPreparation(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty):
    # XXX Totally made up; what is bed preparation, even?
    _time_cost = timedelta(minutes=2)

    def summarize(self):
        return 'Prepare %(quantity)d bed feet for %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class Weed(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty):
    # Time cost for weeding one bed foot of the some crop
    _time_cost = timedelta(minutes=10)

    def summarize(self):
        return 'Weed %(quantity)s bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class Transplant(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, _FlatsTask):
    _time_cost = timedelta(minutes=1)

    use_or_disuse = -1

    def summarize(self):
        return 'Transplant %(quantity)d bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class Harvest(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty):
    _time_cost = timedelta(minutes=2)

    def summarize(self):
        return 'Harvest %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, crop=self.seed.crop.name)



def schedule_planting(crops, seeds):
    # naive approach - schedule everything as early as possible
    schedule = []
    epoch = datetime(year=YEAR, month=1, day=1, hour=0, minute=0, second=0)
    for seed in seeds:
        if seed.beginning_of_season is None or seed.greenhouse_days is None:
            schedule.append(FinishPlanning(seed))
            continue

        # Prep the bed before planting in it
        schedule.append(BedPreparation(
                epoch + timedelta(days=seed.beginning_of_season - 14), seed,
                seed.bed_feet))

        if seed.greenhouse_days != 0:
            # It starts in the greenhouse
            greenhouse_day = timedelta(
                days=seed.beginning_of_season - seed.greenhouse_days)
            schedule.append(SeedFlats(
                    epoch + greenhouse_day, seed, seed.bed_feet))
            schedule.append(Transplant(
                    epoch + timedelta(days=seed.beginning_of_season), seed,
                    seed.bed_feet))
        else:
            schedule.append(DirectSeed(
                    epoch + timedelta(days=seed.beginning_of_season), seed,
                    seed.bed_feet))

        harvest_day = timedelta(
            days=seed.beginning_of_season + seed.maturity_days - seed.greenhouse_days)
        schedule.append(Harvest(epoch + harvest_day, seed, seed.bed_feet))

    schedule.sort(key=lambda event: event.when)

    # Slightly less naive: now spread things out, if there is too much work
    # being done on any particular day.

    # The maximum number of hours of work to schedule per day
    maxManHours = timedelta(hours=3)

    # The time of day at which work starts
    startOfDay = timedelta(hours=8)

    # Walk forward, day by day, from the day of the first job.  For each day,
    # gather up all of the new jobs that can be done from that day forward.
    # Then try to allocate time to those jobs.
    day = schedule[0].date

    # Here are all the jobs which may be scheduled on the day we've gotten up
    # to, ordered by the earliest time they may be done.  Preference will be
    # given to jobs which can be done earlier (based on the weak heuristic that
    # they probably _can't_ be done later; does that hold?  I don't know).
    available = []

    # Here are all the jobs that have been scheduled according to the new,
    # max-man-hours scheduler.
    manHourLimitSchedule = []

    while schedule or available:
        # First move any jobs out of schedule that may be done on or before the
        # day being scheduled.
        while schedule and schedule[0].date <= day:
            available.append(schedule.pop(0))

        # Now schedule some jobs for today.  This is naive, it just schedules
        # jobs in order until one goes over the daily hour limit.
        hours = timedelta(hours=0)
        while available and hours + available[0].duration <= maxManHours:
            event = available.pop(0)
            manHourLimitSchedule.append(event)
            schedDiff = day - event.date
            event.when += startOfDay + hours
            if schedDiff:
                # The event got moved from its originally scheduled time.  Push
                # back any subsequent events that depend on it.
                print 'Moved', event, 'from', event.when, 'to', event.when + schedDiff
                event.when += schedDiff
                for dep in schedule:
                    if dep.seed is event.seed:
                        print dep, 'depends on', event, '; moving back', schedDiff
                        dep.when += schedDiff

            hours += event.duration

        # And move to the next day
        day += timedelta(days=1)

    return manHourLimitSchedule



def summarize_beds(schedule):
    used = 0
    for event in schedule:
        if isinstance(event, (DirectSeed, Transplant)):
            used += event.quantity
        elif isinstance(event, Harvest):
            used -= event.quantity
        else:
            continue
        print 'After', event, 'bed feet in use is', used



def summarize_yields(schedule):
    for event in schedule:
        if isinstance(event, Harvest):
            print 'Harvesting %(amount)s lbs of %(variety)s (%(crop)s) on %(when)s' % dict(
                amount=event.seed.crop.yield_lbs_per_bed_foot * event.quantity,
                variety=event.seed.variety,
                crop=event.seed.crop.name,
                when=event.when)



def main():
    options = CropPlanOptions()
    options.parseOptions()

    crops = load_crops(options['crop-path'])
    seeds = load_seeds(options['seed-path'], crops)

    options['crops'](crops)

    order = generate_seed_order(crops, seeds)

    options['order'](order)

    schedule = schedule_planting(crops, seeds)
    display_schedule = options['schedule']
    if display_schedule is not None:
        display_schedule(schedule)

    options['flats'](schedule)
    if options['beds']:
        summarize_beds(schedule)
    if options['yields']:
        summarize_yields(schedule)


if __name__ == '__main__':
    main()
