# Copyright Jean-Paul Calderone.  See LICENSE file for details.

"""
Unit tests for the crop planning and scheduling module, L{cropplan}.
"""

from datetime import date, datetime, timedelta

from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase
from twisted.python.filepath import FilePath

from cropplan import (
    UnsplittableTask, MissingInformation,
    ITask, FinishPlanning, SeedFlats, DirectSeed, BedPreparation, Weed,
    Transplant, Harvest, Order, Price, Crop, Seed,
    load_crops, load_seeds, create_tasks, schedule_tasks)



def dummyCrop(**kw):
    args = dict(
        name='foo',
        fresh_eating_lbs=3, fresh_eating_weeks=5,
        storage_eating_lbs=6, storage_eating_weeks=10,
        variety=None, harvest_weeks=4, row_feet_per_oz_seed=None,
        yield_lbs_per_bed_foot=2, rows_per_bed=4, in_row_spacing=16,
        _bed_feet=None)
    args.update(kw)
    return Crop(**args)



def dummySeed(crop, **kw):
    args = dict(
        variety='bar', parts_per_crop=1, product_id='1234g',
        greenhouse_days=10, beginning_of_season=90, maturity_days=20,
        end_of_season=200, seeds_per_packet=20, row_foot_per_packet=10,
        seeds_per_oz=500, dollars_per_packet=5.5, dollars_per_hundred=6.5,
        dollars_per_two_fifty=7.6, dollars_per_five_hundred=8.25,
        dollars_per_thousand=20.5, dollars_per_five_thousand=40.5,
        dollars_per_quarter_oz=7.5, dollars_per_half_oz=8.75,
        dollars_per_oz=10.25, dollars_per_eighth_lb=50.5,
        dollars_per_quarter_lb=100.5, dollars_per_half_lb=25.50,
        dollars_per_lb=200.5, row_foot_per_oz=50, dollars_per_mini=25,
        seeds_per_mini=3, row_foot_per_mini=4, harvest_duration=14,
        notes="hello, world")
    args.update(**kw)
    return Seed(crop, **args)


class ComparisonTestsMixin(object):
    def test_identicalEquality(self):
        """
        An instance compares equal to itself.
        """
        instance = self.createFirst()
        self.assertTrue(instance == instance)


    def test_identicalNotUnequality(self):
        """
        An instance does not compare not equal to itself.
        """
        instance = self.createFirst()
        self.assertFalse(instance != instance)


    def test_sameAttributesEquality(self):
        """
        Two instances with the same attributes compare equal.
        """
        first = self.createFirst()
        second = self.createFirst()
        self.assertTrue(first == second)


    def test_sameAttributesNotUnequality(self):
        """
        Two instances with the same attributes do not compare not equal.
        """
        first = self.createFirst()
        second = self.createFirst()
        self.assertFalse(first != second)


    def test_differentAttributesNotEquality(self):
        """
        Two instances with different attributes do not compare equal.
        """
        first = self.createFirst()
        second = self.createSecond()
        self.assertFalse(first == second)


    def test_differentAttributesUnequality(self):
        """
        Two instances with different attributes compare not equal.
        """
        first = self.createFirst()
        second = self.createSecond()
        self.assertTrue(first != second)



class LoadCropsTests(TestCase):
    """
    Tests for L{load_crops} which reads crop data from a CSV file and returns a
    C{dict} containing L{Crop} instances.
    """
    HEADER = (
        "Crop,Eating lb/wk,Fresh Eating Weeks,Storage Pounds Per Week,"
        "Storage Eating Weeks,Variety,Harvest wks,Row Feet Per Ounce Seed,"
        "Yield Pounds Per Foot,Rows / Bed,Spacing (inches),Bed Feet,equipment")

    def _serialize(self, crop):
        format = (
            "%(name)s,%(fresh_eating_lbs)f,%(fresh_eating_weeks)d,"
            "%(storage_eating_lbs)f,%(storage_eating_weeks)d,"
            "%(variety)s,%(harvest_weeks)d,%(row_feet_per_oz_seed)f,"
            "%(yield_lbs_per_bed_foot)f,%(rows_per_bed)d,%(in_row_spacing)d,"
            "%(_bed_feet)s")
        values = vars(crop).copy()
        if values['_bed_feet'] is None:
            values['_bed_feet'] = ''
        return format % values


    def test_load_crops(self):
        """
        Given a L{FilePath} pointing at a CSV file containing a garbage row and
        a header row followed by rows containing a field for each attribute of
        L{Crop}, L{load_crops} constructs a C{dict} with crop names as the keys
        and L{Crop} instances, with fields populated from the file, as values.
        """
        apples = Crop(
            "apples", 5.5, 3, 10, 5, "", 2, 100, 250, 1, 120, 1000)
        path = FilePath(self.mktemp())
        path.setContent(
            "garbage\n%s\n%s\n" % (self.HEADER, self._serialize(apples)))
        crops = load_crops(path)
        self.assertEqual({"apples": apples}, crops)


    def test_implicit_bed_feet(self):
        """
        Rows from the input may omit explicit information about the number of
        bed feet planned, allowing the value to be computed from other fields.
        """
        apples = Crop(
            "apples", 5.5, 3, 10, 5, "", 2, 100, 250, 1, 120, None)
        path = FilePath(self.mktemp())
        path.setContent(
            "garbage\n%s\n%s\n" % (self.HEADER, self._serialize(apples)))
        crops = load_crops(path)
        self.assertEqual({"apples": apples}, crops)


    def test_extra_columns(self):
        """
        Extra columns in the input file that are not part of the L{Crop} are
        ignored.
        """
        apples = Crop(
            "apples", 5.5, 3, 10, 5, "", 2, 100, 250, 1, 120, None)
        path = FilePath(self.mktemp())
        path.setContent(
            "garbage\n%s\n%s\n" % (
                "mystery," + self.HEADER,
                "mystery value," + self._serialize(apples)))
        crops = load_crops(path)
        self.assertEqual({"apples": apples}, crops)



class LoadSeedsTests(TestCase):
    """
    Tests for L{load_seeds} which reads seed variety data from a CSV file and
    returns a C{dict} containing L{Seed} instances.
    """
    HEADER = (
        "Type,Variety,Fresh Eating Generations,Storage Generations,"
        "Bed Ft/fresh eating Generation,Bed ft/Storage generation,"
        "time between generations,Parts Per Crop,Product ID,Greenhouse (days),"
        "Outside,Maturity (total days from seeding),End of season,"
        "seeds/packet,row feet/packet,Seeds/oz,$$/packet,$$/100,$$/250,$$/500,"
        "$$/M,$$/(M>=5),$$/.25OZ,$$/.5OZ,$$/oz,$$/.125LB,$$/.25LB,$$/.5LB,"
        "$$/LB,ft/oz,$$/mini,Seeds/mini,row feet/mini,Harvest Duration (Days),"
        "Notes")

    def _serialize(self, seed):
        format = (
            "%(crop)s,%(variety)s,%(parts_per_crop)d,%(product_id)s,"
            "%(greenhouse_days)s,%(beginning_of_season)s,%(maturity_days)d,"
            "%(end_of_season)s,%(seeds_per_packet)d,%(row_foot_per_packet)d,"
            "%(seeds_per_oz)d,%(dollars_per_packet)f,%(dollars_per_hundred)f,"
            "%(dollars_per_two_fifty)f,%(dollars_per_five_hundred)f,"
            "%(dollars_per_thousand)f,%(dollars_per_five_thousand)f,"
            "%(dollars_per_quarter_oz)f,%(dollars_per_half_oz)f,"
            "%(dollars_per_oz)f,%(dollars_per_eighth_lb)f,"
            "%(dollars_per_quarter_lb)f,%(dollars_per_half_lb)f,"
            "%(dollars_per_lb)f,%(row_foot_per_oz)f,%(dollars_per_mini)f,"
            "%(seeds_per_mini)d,%(row_foot_per_mini)f,%(harvest_duration)d,"
            "%(notes)s")
        values = vars(seed).copy()
        dates = ["beginning_of_season", "end_of_season"]
        for k in dates:
            d = values[k]
            d = date(1980, 1, 1) + timedelta(days=d)
            values[k] = "%d/%d/%d" % (d.month, d.day, d.year)
        values['crop'] = values['crop'].name
        if values['greenhouse_days'] is None:
            values['greenhouse_days'] = ""
        # LA LA
        values['dollars_per_five_thousand'] /= 5.0
        return format % values


    def test_load_seeds(self):
        """
        Given a L{FilePath} pointing at a CSV file containing a header row
        followed by rows containing a field for each attribute of L{Crop}, and a
        C{dict} like the one returned by L{load_crops}, L{load_seeds} constructs
        a C{list} of L{Seed} instances, with fields populated from the file.
        """
        apples = Crop(
            "apples", 5.5, 3, 10, 5, "", 2, 100, 250, 1, 120, 1000)
        crops = {'apples': apples}

        wealthy = Seed(
            apples, 'wealthy', 1, "", None, 91, 25, 150, 100, 10,
            1000, 1.50, 2.50, 3.50, 4.50, 5.50, 6.50, 7.50, 8.50, 9.50, 10.50,
            11.50, 12.50, 13.50, 25, 0.50, 15, 3, 14, "")

        path = FilePath(self.mktemp())
        path.setContent(
            "%s\n%s\n" % (self.HEADER, self._serialize(wealthy)))

        seeds = load_seeds(path, crops)
        self.assertEqual([wealthy], seeds)



class CropTests(TestCase, ComparisonTestsMixin):
    """
    Tests for L{Crop}, a representation of a particular crop but not any
    specific variety of that crop.
    """
    def createFirst(self):
        return dummyCrop(name='foo')


    def createSecond(self):
        return dummyCrop(name='bar')


    def test_bed_feet(self):
        """
        L{Crop.bed_feet} is computed based on the total yield required,
        considering the estimated productivity of the crop per bed foot.
        """
        crop = dummyCrop(
            fresh_eating_weeks=2, fresh_eating_lbs=3,
            storage_eating_weeks=4, storage_eating_lbs=5,
            yield_lbs_per_bed_foot=0.5)
        self.assertEqual((2 * 3 + 4 * 5) * 2.0, crop.bed_feet)


    def test_bed_feet_fallback(self):
        """
        If a crop's estimated productivity is not supplied, the C{_bed_feet}
        attribute can provide a fallback value for the value of
        C{Crop.bed_feet}.
        """
        crop = dummyCrop(
            fresh_eating_weeks=2, fresh_eating_lbs=3,
            storage_eating_weeks=4, storage_eating_lbs=5,
            yield_lbs_per_bed_foot=None, _bed_feet=4.5)
        self.assertEqual(4.5, crop.bed_feet)


    def test_invalid_yield_lbs_per_bed_foot(self):
        """
        L{Crop.yield_lbs_per_bed_foot} must be specified as C{None} or a
        positive number.  Otherwise a L{ValueError} is raised.
        """
        self.assertRaises(ValueError, dummyCrop, yield_lbs_per_bed_foot=0)
        self.assertRaises(ValueError, dummyCrop, yield_lbs_per_bed_foot=-1)



class SeedTests(TestCase, ComparisonTestsMixin):
    """
    Tests for L{Seed}, a representation of a particular variety of a particular
    crop.
    """
    def setUp(self):
        self.crop = dummyCrop()


    def createFirst(self):
        return dummySeed(self.crop, variety='foo')


    def createSecond(self):
        return dummySeed(self.crop, variety='bar')


    def test_unplantedCrop(self):
        """
        L{Seed}s associated with a L{Crop} for which no bed feet are being
        planted report their own bed feet as C{0}.
        """
        # If we have no yield, we need no bed feet.
        self.crop.fresh_eating_weeks = 0
        self.crop.storage_eating_weeks = 0

        seed = dummySeed(self.crop)
        self.assertEqual(0, seed.bed_feet)



class SeedOrderTests(TestCase):
    """
    Tests for L{Seed.order}, a method for determining how much of a seed to buy,
    and in what packaging.
    """
    def dummySeed(self, crop, **kw):
        """
        A version of L{dummySeed} which removes all default price information.
        """
        args = dict(
            dollars_per_packet=None, dollars_per_hundred=None,
            dollars_per_two_fifty=None, dollars_per_five_hundred=None,
            dollars_per_thousand=None, dollars_per_five_thousand=None,
            dollars_per_quarter_oz=None, dollars_per_half_oz=None,
            dollars_per_oz=None, dollars_per_eighth_lb=None,
            dollars_per_quarter_lb=None, dollars_per_half_lb=None,
            dollars_per_lb=None, dollars_per_mini=None,
            )
        args.update(kw)
        return dummySeed(crop, **args)


    def test_missingPrices(self):
        """
        L{Seed.order} raises L{MissingInformation} if there is no price
        information.
        """
        crop = dummyCrop()
        seed = self.dummySeed(crop)
        self.assertRaises(MissingInformation, seed.order, 100)


    def test_orderMinimumSufficient(self):
        """
        L{Seed.order} takes a number of bed feet and returns a list of L{Order}
        instances which represent enough seed to plant that number of bed feet
        at the lowest price possible given the available price data.
        """
        crop = dummyCrop(rows_per_bed=2)
        seed = self.dummySeed(
            crop, dollars_per_packet=2.0, row_foot_per_packet=10)
        order = seed.order(25)
        price = Price('packet', 2.0, 10)
        self.assertEqual([Order(seed, 70, price)], order)



class PriceTests(TestCase, ComparisonTestsMixin):
    """
    Tests for L{Price}, representing a particular item and its cost.
    """
    def createFirst(self):
        return Price('packet', 3.50, 10)


    def createSecond(self):
        return Price('mini', 2, 5)



class OrderTests(TestCase, ComparisonTestsMixin):
    """
    Tests for L{Order}, representing a quantity of an item to purchase.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)
        self.price = self.seed.prices[0]


    def createFirst(self):
        return Order(self.seed, 10, self.price)


    def createSecond(self):
        return Order(self.seed, 20, self.price)



class TaskTestsMixin(object):
    """
    L{TaskTestsMixin} is a mixin for L{TestCase} subclasses which defines
    several test methods common to any kind of task.
    """
    def createTask(self):
        """
        Create a new instance of a kind of task.

        Override this in a subclass to create the kind of task that subclass is
        testing.
        """
        raise NotImplementedError(
            "%s did not implement createTask" % (self.__class__,))


    def test_interface(self):
        """
        All tasks provide L{ITask}.
        """
        task = self.createTask()
        self.assertTrue(verifyObject(ITask, task))


    def test_split(self):
        """
        L{ITask.split} returns a tuple of two L{ITask} providers.  The sum of
        the C{duration} of the two new tasks is the same as the duration of the
        original task, but the C{duration} of the first task is no greater than
        the duration passed to C{split}.
        """
        task = self.createTask()
        first, second = task.split(task.duration / 5 * 3)
        self.assertEqual(first.duration, task.duration / 5 * 3)
        self.assertEqual(second.duration, task.duration / 5 * 2)

        # The other attributes should be the same
        self.assertEqual(first.when, task.when)
        self.assertEqual(second.when, task.when)

        self.assertEqual(first.seed, task.seed)
        self.assertEqual(second.seed, task.seed)


    def test_str(self):
        """
        The result of C{str} on a task is the task summary in parenthesis.
        """
        task = self.createTask()
        self.assertEqual("(%s)" % (task.summarize(),), str(task))



class FinishPlanningTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{FinishPlanning}, representing a task for finishing planning
    related to a particular seed.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{FinishPlanning} task using an arbitrary seed variety.
        """
        return FinishPlanning(dummySeed(dummyCrop()))


    def createFirst(self):
        return FinishPlanning(self.seed)


    def createSecond(self):
        return FinishPlanning(dummySeed(self.crop, variety='quux'))


    def test_split(self):
        """
        L{FinishPlanning.split} raises L{UnsplittableTask}.
        """
        self.assertRaises(
            UnsplittableTask,
            FinishPlanning(dummySeed(dummyCrop())).split, timedelta())


    def test_summarize(self):
        """
        L{FinishPlanning.summarize} identifies the task as planning and includes
        the name of the seed and crop it is for.
        """
        task = self.createTask()
        self.assertEqual("Finish planning bar (foo)", task.summarize())



class SeedFlatsTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{SeedFlats}, representing a task for sowing seeds of a particular
    variety into flats.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{SeedFlats} task using an arbitrary date, seed variety,
        and quantity.
        """
        return SeedFlats(datetime(2000, 6, 12, 8, 0, 0), self.seed, 50)


    def createFirst(self):
        return SeedFlats(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return SeedFlats(datetime(2001, 6, 2), self.seed, 25)


    def test_summarize(self):
        """
        L{SeedFlats.summarize} identifies the task as seeding flats and includes
        the name of the seed and crop it is for as well as the number of bed
        feet.
        """
        task = self.createTask()
        self.assertEqual(
            'Seed flats for 50 bed feet of bar (foo)',
            task.summarize())



class DirectSeedTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{DirectSeed}, representing a task for sowing seeds of a
    particular variety directly into a bed.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{DirectSeed} task using an arbitrary date, seed variety,
        and quantity.
        """
        return DirectSeed(datetime(2001, 7, 2, 9, 30, 0), self.seed, 10)


    def createFirst(self):
        return DirectSeed(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return DirectSeed(datetime(2001, 6, 2), self.seed, 25)


    def test_summarize(self):
        """
        L{DirectSeed.summarize} identifies the task as direct seeding and
        includes the name of the seed and crop it is for as well as the number
        of bed feet.
        """
        task = self.createTask()
        self.assertEqual(
            "Direct seed 10 bed feet of bar (foo)", task.summarize())



class BedPreparationTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{BedPreparation}, representing a task for preparing bed space for
    seeds of a particular variety (without specifying the details of that
    preparation; it may be amending, weeding, etc).
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{BedPreparation} task using an arbitrary date, seed
        variety, and quantity.
        """
        return BedPreparation(datetime(2002, 5, 25, 10, 15, 0), self.seed, 25)


    def createFirst(self):
        return BedPreparation(datetime(2003, 5, 16, 9, 0, 0), self.seed, 25)


    def createSecond(self):
        return BedPreparation(datetime(2003, 5, 16, 9, 0, 0), self.seed, 50)



class WeedTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{Weed}, representing a task for weeding bed space already planted
    in a particular variety.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{Weed} task using an arbitrary date, seed variety, and
        quantity.
        """
        return Weed(datetime(2003, 8, 15, 11, 0, 0), self.seed, 50)


    def createFirst(self):
        return Weed(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return Weed(datetime(2001, 6, 1), self.seed, 75)



class TransplantTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{Transplant}, representing a task for transplanting seedlings of a
    particular variety from flats into bed space.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{Transplant} task using an arbitrary date, seed variety,
        and quantity.
        """
        return Transplant(datetime(2004, 7, 1, 8, 0, 0), self.seed, 15)


    def createFirst(self):
        return Transplant(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return Transplant(datetime(2001, 6, 1), self.seed, 75)



class HarvestTests(TestCase, TaskTestsMixin, ComparisonTestsMixin):
    """
    Tests for L{Harvest}, representing a task for harvesting produce from bed
    space planted in particular variety.
    """
    def setUp(self):
        self.crop = dummyCrop()
        self.seed = dummySeed(self.crop)


    def createTask(self):
        """
        Create a new L{Harvest} task using an arbitrary date, seed variety, and
        quantity.
        """
        return Harvest(datetime(2005, 9, 15, 9, 0, 0), self.seed, 25)


    def createFirst(self):
        return Harvest(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return Harvest(datetime(2001, 6, 1), self.seed, 75)



class CreateTasksTests(TestCase):
    """
    Tests for L{create_tasks}, a function for creating the list of necessary
    tasks from crop and seed information.
    """
    def test_noTasksForNoFeet(self):
        """
        L{create_tasks} creates no tasks at all for a seed with C{bed_feet} set
        to C{0}.
        """
        crop = dummyCrop()
        crops = {'foo': crop}
        seedA = dummySeed(crop, parts_per_crop=0)
        seedB = dummySeed(crop, parts_per_crop=1)

        # Just a sanity check
        self.assertEqual(0, seedA.bed_feet)

        seeds = [seedA, seedB]
        tasks = create_tasks(crops, seeds)
        for task in tasks:
            if task.seed is seedA:
                self.fail(
                    "Created a task for a seed with no bed feet: %r" % (
                        task,))


    def test_noBeginningOfSeason(self):
        """
        L{create_tasks} creates a L{FinishPlanning} for a seed with no beginning
        of season information.
        """
        crop = dummyCrop()
        crops = {'foo': crop}
        seed = dummySeed(crop, beginning_of_season=None)
        seeds = [seed]
        tasks = create_tasks(crops, seeds)
        self.assertEqual([FinishPlanning(seed)], tasks)


    def test_noGreenhouseDays(self):
        """
        L{create_tasks} creates a L{FinishPlanning} for a seed with no
        greenhouse information.
        """
        crop = dummyCrop()
        crops = {'foo': crop}
        seed = dummySeed(crop, greenhouse_days=None)
        seeds = [seed]
        tasks = create_tasks(crops, seeds)
        self.assertEqual([FinishPlanning(seed)], tasks)



class ScheduleTasksTests(TestCase):
    """
    Tests for L{schedule_tasks}
    """
    def test_eagerScheduling(self):
        """
        When there is no contention amongst necessary tasks, L{schedule_tasks}
        leaves the scheduling of tasks alone.
        """
        crop = dummyCrop()
        seed = dummySeed(crop)
        tasks = [SeedFlats(datetime(2012, 5, 1), seed, 10)]
        schedule = schedule_tasks(tasks)
        # Compare against a new copy, to ensure that no unexpected mutation of
        # the SeedFlats instance happened.
        self.assertEqual(
            [SeedFlats(datetime(2012, 5, 1, 8, 0, 0), seed, 10)],
            schedule)


    def test_delayConflicting(self):
        """
        When there are multiple tasks scheduled to happen at the same time,
        L{schedule_tasks} pushes one of them back so it begins after the other
        one ends.
        """
        crop = dummyCrop()
        seedA = dummySeed(crop)
        seedB = dummySeed(crop)
        tasks = [
            SeedFlats(datetime(2012, 5, 1), seedA, 10),
            SeedFlats(datetime(2012, 5, 1), seedB, 10)]
        schedule = schedule_tasks(tasks)
        self.assertEqual(
            [SeedFlats(datetime(2012, 5, 1, 8, 0, 0), seedA, 10),
             SeedFlats(datetime(2012, 5, 1, 8, 20, 0), seedB, 10)],
            schedule)


    def test_postponeConflicting(self):
        """
        When a task must be delayed but there are not enough hours remaining in
        the day on which it was originally scheduled, it is moved to the
        beginning of the following day.
        """
        crop = dummyCrop()
        seedA = dummySeed(crop)
        seedB = dummySeed(crop)
        tasks = [
            SeedFlats(datetime(2012, 5, 1), seedA, 90),
            SeedFlats(datetime(2012, 5, 1), seedB, 90)]
        schedule = schedule_tasks(tasks)
        self.assertEqual(
            [SeedFlats(datetime(2012, 5, 1, 8, 0, 0), seedA, 90),
             SeedFlats(datetime(2012, 5, 2, 8, 0, 0), seedB, 90)],
            schedule)


    def test_splitLarge(self):
        """
        If a task takes more time than there is left in the day on which it is
        scheduled, it is split into two tasks and the remainder is moved to the
        next day.
        """
        crop = dummyCrop()
        seed = dummySeed(crop)
        tasks = [SeedFlats(datetime(2012, 5, 1), seed, 170)]
        schedule = schedule_tasks(tasks)
        self.assertEqual(
            [SeedFlats(datetime(2012, 5, 1, 8, 0, 0), seed, 90),
             SeedFlats(datetime(2012, 5, 2, 8, 0, 0), seed, 80)],
            schedule)


    def test_splitLargeNotFirst(self):
        """
        If a task must be split over two days and it is not the first task done
        on the first day, only the time remaining in the first day is allocated
        to the first part of the split up task.  In other words, the total
        amount of time for tasks already done on a day and the amount of time
        for a piece of a split task still do not exceed the daily hour limit.
        """
        crop = dummyCrop()
        seedA = dummySeed(crop)
        seedB = dummySeed(crop)
        tasks = [SeedFlats(datetime(2012, 5, 1), seedA, 60),
                 SeedFlats(datetime(2012, 5, 1), seedB, 65)]
        schedule = schedule_tasks(tasks)
        self.assertEqual(
            [SeedFlats(datetime(2012, 5, 1, 8, 0, 0), seedA, 60),
             SeedFlats(datetime(2012, 5, 1, 10, 0, 0), seedB, 30),
             SeedFlats(datetime(2012, 5, 2, 8, 0, 0), seedB, 35)],
            schedule)
