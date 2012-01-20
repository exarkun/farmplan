# Copyright Jean-Paul Calderone.  See LICENSE file for details.

"""
Tools for crop planning and scheduling.

TODO: Describe options and general usage

TODO: Describe data (csv) format

TODO: Describe text and plot outputs

TODO: Describe seed ordering

TODO: Describe scheduling plain text and ical output

TODO: Describe resource (flats) usage

TODO: Describe yield estimation

TODO: Clean up extra text output on stdout
"""

from csv import reader
from sys import argv
from math import ceil
from itertools import groupby
from datetime import date, datetime, timedelta
from collections import defaultdict

from zope.interface import Attribute, Interface, implements

from pytz import timezone

from dateutil.rrule import SU

from vobject import iCalendar

from twisted.python.log import msg
from twisted.python.filepath import FilePath
from twisted.python.usage import Options
from twisted.python.util import FancyEqMixin

from epsilon.structlike import record

YEAR = 2012


class UnsplittableTask(Exception):
    """
    An attempt was made to split a task which cannot be sub-divided.
    """



class ITask(Interface):
    """
    Represent an activity that needs to be performed, probably by a person.
    """
    seed = Attribute(
        """
        A L{Seed} instance indicating what seed variety this task is most
        directly related to.
        """)


    when = Attribute(
        """
        A L{datetime.datetime} instance giving the time at which point this task
        is to be done.
        """)


    duration = Attribute(
        """
        A L{datetime.timedelta} instance giving an estimate of how long this
        task will take to complete.
        """)


    def split(duration):
        """
        Divide this task up into two new tasks which are identical except for
        the amount of work they represent.  Taken together, the two new tasks
        should be equivalent to this task.  One of the new tasks is guaranteed
        not to take longer than C{duration}.

        @return: A C{tuple} of two L{ITask} providers.
        """



class ComparableRecord(FancyEqMixin, object):
    compareAttributes = property(lambda self: self.__names__)



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
    tz = timezone('US/Eastern')
    cal = iCalendar()
    for event in schedule:
        when = event.when.replace(tzinfo=tz)
        vevent = cal.add('vevent')
        vevent.add('dtstart').value = when
        vevent.add('dtend').value = when + event.duration

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
    order_total = 0.0
    ideal_total = 0.0

    for item in order:

        cost = item.cost()
        order_total += cost
        ideal_total += cost / item.excess()

        bed_feet = item.row_feet / item.seed.crop.rows_per_bed
        print (
            'Plant %(bed_feet)s feet of %(variety)s (%(crop)s - Product ID %(product_id)s) '
            'at $%(cost)5.2f (ideally %(ideal)5.2f; %(buy)5.2f%%)' % {
                'bed_feet': bed_feet, 'variety': item.seed.variety,
                'crop': item.seed.crop.name, 'cost': cost,
                'ideal': cost / item.excess(), 'buy': item.excess() * 100,
                'product_id': item.seed.product_id})

    for item in order:
        total_yield = item.seed.crop.total_yield
        if total_yield == 0:
            cost = '(unknown yield)'
        else:
            cost = '%5.2f' % (item.cost() / total_yield,)
        print '%(variety)s (%(crop)s - Product ID %(product_id)s) $%(cost)s' % dict(
            variety=item.seed.variety, crop=item.seed.crop.name,
            cost=cost, product_id=item.seed.product_id)

    for item in order:
        print '\t$%(cost)5.2f %(count)d %(kind)s of %(variety)s (%(crop)s - Product ID %(product_id)s)' % dict(
            cost=item.cost(), count=item.count, kind=item.price.kind,
            variety=item.seed.variety, crop=item.seed.crop.name,
            product_id=item.seed.product_id)
    print 'Total\t$%(cost)5.2f (ideal $%(ideal)5.2f)' % dict(
        cost=order_total, ideal=ideal_total)
    return order



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
        self['flats'] = display_nothing


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
        'yield_lbs_per_bed_foot rows_per_bed in_row_spacing _bed_feet'),
           ComparableRecord):
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

        if (self.yield_lbs_per_bed_foot is not None
            and self.yield_lbs_per_bed_foot <= 0):
            raise ValueError(
                "%s yield_lbs_per_bed_foot must be None (if unknown) or "
                "a positive number, not %r" % (
                    self.name, self.yield_lbs_per_bed_foot))

        self.varieties = []


    @property
    def bed_feet(self):
        if self.total_yield is None or self.yield_lbs_per_bed_foot is None:
            if self._bed_feet is None:
                raise RuntimeError("Who knows? %r" % (self,))
            return self._bed_feet
        return self.total_yield / self.yield_lbs_per_bed_foot


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
        'crop variety parts_per_crop product_id greenhouse_days beginning_of_season maturity_days '
        'end_of_season seeds_per_packet row_foot_per_packet seeds_per_oz '
        'dollars_per_packet dollars_per_hundred dollars_per_two_fifty '
        'dollars_per_five_hundred dollars_per_thousand dollars_per_five_thousand dollars_per_quarter_oz '
        'dollars_per_half_oz dollars_per_oz dollars_per_eighth_lb dollars_per_quarter_lb '
        'dollars_per_half_lb dollars_per_lb row_foot_per_oz dollars_per_mini '
        'seeds_per_mini row_foot_per_mini harvest_duration notes'),
           ComparableRecord):
    """
    @ivar crop: The name of the crop - matches the name of one of the L{Crop}
        instances.

    @ivar variety: The name of a specific variety or cultivar of this crop.

    @ivar parts_per_crop: Within the crop of which this seed is a variety, the
        ratio of this seed to other varieties of this crop.  The total quantity
        to plant is determined by the crop (eg 100 feet of tomatoes); this
        allows the control of relative rates (eg for 75 feet of sauce tomatoes
        and 25 feet of cherry tomatoes, give sauce tomatoes a parts_per_crop of
        3 and the cherry tomatoes a parts_per_crop of 1).

    @ivar product_id: A string giving the seed company product identifier for
        this seed variety.

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

    @ivar dollars_per_five_thousand: If seeds are sold by the 5000, the price of
        5000 seeds of this variety.  May be C{None}, etc.

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
    def __init__(self, *args, **kwargs):
        super(Seed, self).__init__(*args, **kwargs)
        self.crop.varieties.append(self)


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
    price_per_five_thousand = _PriceComputer('five thousand', 'dollars_per_five_thousand', None, None, 5000)

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

        # Get rid of anything without a known length, we can't meaningfully
        # select these for the order.
        known_prices = [
            p for p in prices if p.row_foot_increment is not None]

        # How much excess to build in to the order
        minimum_overrun = 0.3

        required_row_feet = self.crop.rows_per_bed * bed_feet
        required_row_feet *= (1 + minimum_overrun)

        order_prices = {}
        remaining_row_feet = required_row_feet

        while remaining_row_feet > 0:

            # Sort the prices by the price per row foot, accounting for the
            # effective price increase incurred by wasted seed.
            known_prices.sort(key=lambda p: p.dollars / min(p.row_foot_increment, remaining_row_feet))

            # Select the cheapest thing according to that scheme
            the_price = known_prices[0]

            order_prices[the_price] = order_prices.get(the_price, 0) + 1
            remaining_row_feet -= the_price.row_foot_increment

        return [
            Order(self, price.row_foot_increment * count, price)
            for (price, count)
            in order_prices.items()]


    @property
    def bed_feet(self):
        """
        The number of bed feet of this variety of this crop to plant.  This is
        determined by looking at the total bed feet for the crop and dividing it
        up amongst all of the varieties being planted.
        """
        total_weight = sum(seed.parts_per_crop for seed in self.crop.varieties)
        my_weight = self.parts_per_crop
        my_proportion = float(my_weight) / float(total_weight)
        return float(self.crop.bed_feet) * my_proportion



def load_crops(path):
    data = reader(path.open())
    # Ignore the first two rows
    data.next()
    headers = data.next()
    crops = {}
    defaults = defaultdict(float)
    defaults['Yield Pounds Per Foot'] = None
    for row in data:
        crop = Crop(
            row[0],
            *[(float(field) if field != '' else defaults[name])
              for (name, field)
              in zip(headers[1:], row[1:])])
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
        nextField = iter(row).next

        crop = crops[nextField()]
        seed = Seed(
            crop=crop, variety=nextField(), parts_per_crop=parse_or_default(int, nextField(), 1),
            product_id=nextField(), greenhouse_days=parse_or_default(int, nextField(), None),
            beginning_of_season=parse_or_default(parse_date, nextField(), None),
            maturity_days=parse_or_default(int, nextField(), None),
            end_of_season=parse_or_default(parse_date, nextField(), None),
            seeds_per_packet=parse_or_default(int, nextField(), None),
            row_foot_per_packet=parse_or_default(float, nextField(), None),
            seeds_per_oz=parse_or_default(float, nextField(), None),
            dollars_per_packet=parse_or_default(float, nextField(), None),
            dollars_per_hundred=parse_or_default(float, nextField(), None),
            dollars_per_two_fifty=parse_or_default(float, nextField(), None),
            dollars_per_five_hundred=parse_or_default(float, nextField(), None),
            dollars_per_thousand=parse_or_default(float, nextField(), None),
            dollars_per_five_thousand=parse_or_default(lambda s: float(s) * 5, nextField(), None),
            dollars_per_quarter_oz=parse_or_default(float, nextField(), None),
            dollars_per_half_oz=parse_or_default(float, nextField(), None),
            dollars_per_oz=parse_or_default(float, nextField(), None),
            dollars_per_eighth_lb=parse_or_default(float, nextField(), None),
            dollars_per_quarter_lb=parse_or_default(float, nextField(), None),
            dollars_per_half_lb=parse_or_default(float, nextField(), None),
            dollars_per_lb=parse_or_default(float, nextField(), None),
            row_foot_per_oz=parse_or_default(float, nextField(), None),
            dollars_per_mini=parse_or_default(float, nextField(), None),
            seeds_per_mini=parse_or_default(int, nextField(), None),
            row_foot_per_mini=parse_or_default(float, nextField(), None),
            harvest_duration=parse_or_default(int, nextField(), None),
            notes=nextField(),
            )
        seeds.append(seed)
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
        for seed in varieties:
            bed_feet = seed.bed_feet
            if bed_feet > 0:
                order = seed.order(bed_feet)
                if isinstance(order, MissingInformation):
                    msg(order.message)
                else:
                    for o in order:
                        yield o
            else:
                message = (
                    'Not ordering %(variety)s (%(name)s) because it has no bed'
                    'feet allocated.')
                msg(format=message % dict(variety=seed.variety, name=seed.crop.name))



class _ByTheFootTask(object):
    @property
    def duration(self):
        # Cannot multiply timedelta and float; so round up to the next integer
        # number of bed feet.  It's close enough for scheduling considerations.
        return self._time_cost * int(ceil(self.quantity))


    def split(self, duration):
        """
        Create two new tasks, dividing the footage between them so that one
        comes in under the requested duration.
        """
        ratio = duration.total_seconds() / self.duration.total_seconds()
        quantity = int(ratio * self.quantity)
        remaining = self.quantity - quantity
        return (
            self.__class__(self.when, self.seed, quantity),
            self.__class__(self.when, self.seed, remaining),
            )



class _DayTask(object):
    @property
    def date(self):
        return self.when.date()


class _Pretty(object):
    def __str__(self):
        return '(%s)' % (self.summarize(),)


# record needs better support for inheritance
class FinishPlanning(record('seed'), _DayTask, _Pretty, ComparableRecord):
    implements(ITask)

    # Get this to sort first
    when = datetime(YEAR, 1, 1, 0, 0, 0)

    # Amount of time an event of this type takes to complete
    duration = timedelta(minutes=30)

    def summarize(self):
        return 'Finish planning %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, crop=self.seed.crop.name)


    def split(self, duration):
        raise UnsplittableTask()



class _FlatsTask(object):
    def required_flats(self):
        crop = self.seed.crop
        seedlings = self.quantity / (crop.in_row_spacing / 12.0) * crop.rows_per_bed
        return ceil(seedlings / 72.0) * self.use_or_disuse



class SeedFlats(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, _FlatsTask, ComparableRecord):
    implements(ITask)

    # Time cost in seconds for seeding one bed foot into a flat
    # XXX Should be based on what's being seeded due to spacing differences
    _time_cost = timedelta(minutes=2)

    use_or_disuse = 1

    def summarize(self):
        return 'Seed flats for %(quantity)d bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class DirectSeed(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, ComparableRecord):
    implements(ITask)

    # Time cost for direct seeding one bed foot
    # XXX I totally made this up
    _time_cost = timedelta(seconds=30)

    def summarize(self):
        return 'Direct seed %(quantity)d bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class BedPreparation(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, ComparableRecord):
    implements(ITask)

    # XXX Totally made up; what is bed preparation, even?
    _time_cost = timedelta(minutes=2)

    def summarize(self):
        return 'Prepare %(quantity)d bed feet for %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class Weed(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, ComparableRecord):
    implements(ITask)

    # Time cost for weeding one bed foot of the some crop
    _time_cost = timedelta(minutes=10)

    def summarize(self):
        return 'Weed %(quantity)s bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class Transplant(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, _FlatsTask, ComparableRecord):
    implements(ITask)

    _time_cost = timedelta(minutes=1)

    use_or_disuse = -1

    def summarize(self):
        return 'Transplant %(quantity)d bed feet of %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, quantity=self.quantity,
            crop=self.seed.crop.name)



class Harvest(record('when seed quantity'), _ByTheFootTask, _DayTask, _Pretty, ComparableRecord):
    implements(ITask)

    _time_cost = timedelta(minutes=2)

    def summarize(self):
        return 'Harvest %(variety)s (%(crop)s)' % dict(
            variety=self.seed.variety, crop=self.seed.crop.name)



def create_tasks(crops, seeds):
    # naive approach - schedule everything as early as possible
    tasks = []
    epoch = datetime(year=YEAR, month=1, day=1, hour=0, minute=0, second=0)
    for seed in seeds:
        if seed.beginning_of_season is None or seed.greenhouse_days is None:
            tasks.append(FinishPlanning(seed))
            continue

        # Avoid creating tasks for things that are not actually being planted
        if seed.bed_feet == 0:
            continue

        # Prep the bed before planting in it
        tasks.append(BedPreparation(
                epoch + timedelta(days=seed.beginning_of_season - 14), seed,
                seed.bed_feet))

        if seed.greenhouse_days != 0:
            # It starts in the greenhouse
            greenhouse_day = timedelta(
                days=seed.beginning_of_season - seed.greenhouse_days)
            tasks.append(SeedFlats(
                    epoch + greenhouse_day, seed, seed.bed_feet))
            tasks.append(Transplant(
                    epoch + timedelta(days=seed.beginning_of_season), seed,
                    seed.bed_feet))
        else:
            tasks.append(DirectSeed(
                    epoch + timedelta(days=seed.beginning_of_season), seed,
                    seed.bed_feet))

        harvest_day = timedelta(
            days=seed.beginning_of_season + seed.maturity_days - seed.greenhouse_days)
        tasks.append(Harvest(epoch + harvest_day, seed, seed.bed_feet))

    tasks.sort(key=lambda event: event.when)
    return tasks



def schedule_tasks(tasks):
    # Slightly less naive: now spread things out, if there is too much work
    # being done on any particular day.

    # The maximum number of hours of work to schedule per day
    maxManHours = timedelta(hours=3)

    # The maximum amount of time to waste at the end of a day (in other words,
    # the smallest piece of a larger task to break off and schedule at the end
    # of a day instead of moving the entire task to the next day).
    endOfDayWaste = timedelta(minutes=30)

    # The time of day at which work starts
    startOfDay = timedelta(hours=8)

    # Walk forward, day by day, from the day of the first job.  For each day,
    # gather up all of the new jobs that can be done from that day forward.
    # Then try to allocate time to those jobs.
    day = tasks[0].date

    # Here are all the jobs which may be scheduled on the day we've gotten up
    # to, ordered by the earliest time they may be done.  Preference will be
    # given to jobs which can be done earlier (based on the weak heuristic that
    # they probably _can't_ be done later; does that hold?  I don't know).
    available = []

    # Here are all the jobs that have been scheduled according to the new,
    # max-man-hours scheduler.
    manHourLimitSchedule = []

    while tasks or available:
        # First move any jobs out of schedule that may be done on or before the
        # day being scheduled.
        while tasks and tasks[0].date <= day:
            available.append(tasks.pop(0))

        # Now schedule some jobs for today.  This is naive, it just schedules
        # jobs in order until one goes over the daily hour limit.
        hours = timedelta(hours=0)
        while True:
            if not available:
                # All done
                break

            if hours + available[0].duration > maxManHours:
                # This task does not fit in this day as is.

                if maxManHours > hours + endOfDayWaste:
                    # There is enough time left today to split the task up.
                    replacements = available[0].split(maxManHours - hours)
                    # Replace the original with the (two) split up tasks.  Then
                    # fall through to the code for handling available[0] below.
                    available[:1] = replacements
                else:
                    # There isn't enough time left today to bother, move on to
                    # the next day.
                    break

            event = available.pop(0)
            manHourLimitSchedule.append(event)
            schedDiff = day - event.date
            event.when += startOfDay + hours
            if schedDiff:
                # The event got moved from its originally scheduled time.  Push
                # back any subsequent events that depend on it.
                event.when += schedDiff
                for dep in tasks:
                    if dep.seed is event.seed:
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



def main(args=None):
    if args is None:
        args = argv[1:]

    options = CropPlanOptions()
    options.parseOptions(args)

    crops = load_crops(options['crop-path'])
    seeds = load_seeds(options['seed-path'], crops)

    options['crops'](crops)

    order = make_order(crops, seeds)

    options['order'](order)

    tasks = create_tasks(crops, seeds)
    schedule = schedule_tasks(tasks)
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
