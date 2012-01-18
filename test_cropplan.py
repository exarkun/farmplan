# Copyright Jean-Paul Calderone.  See LICENSE file for details.

"""
Unit tests for the crop planning and scheduling module, L{cropplan}.
"""

from datetime import datetime, timedelta

from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase

from cropplan import (
    UnsplittableTask,
    ITask, FinishPlanning, SeedFlats, DirectSeed, BedPreparation, Weed,
    Transplant, Harvest, Crop, Seed, create_tasks, schedule_tasks)



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



class CropTests(TestCase, ComparisonTestsMixin):
    """
    Tests for L{Crop}, a representation of a particular crop but not any
    specific variety of that crop.
    """
    def createFirst(self):
        return dummyCrop(name='foo')


    def createSecond(self):
        return dummyCrop(name='bar')



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
        return SeedFlats(datetime(2000, 6, 12, 8, 0, 0), object(), 50)


    def createFirst(self):
        return SeedFlats(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return SeedFlats(datetime(2001, 6, 2), self.seed, 25)



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
        return DirectSeed(datetime(2001, 7, 2, 9, 30, 0), object(), 10)


    def createFirst(self):
        return DirectSeed(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return DirectSeed(datetime(2001, 6, 2), self.seed, 25)



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
        return BedPreparation(datetime(2002, 5, 25, 10, 15, 0), object(), 25)


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
        return Weed(datetime(2003, 8, 15, 11, 0, 0), object(), 50)


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
        return Transplant(datetime(2004, 7, 1, 8, 0, 0), object(), 15)


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
        return Harvest(datetime(2005, 9, 15, 9, 0, 0), object(), 25)


    def createFirst(self):
        return Harvest(datetime(2001, 6, 1), self.seed, 25)


    def createSecond(self):
        return Harvest(datetime(2001, 6, 1), self.seed, 75)



class CreateTasksTests(TestCase):
    """
    Tests for L{create_tasks}, a function for creating the list of necessary
    tasks from crop and seed information.
    """
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
