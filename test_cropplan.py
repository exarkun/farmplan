# Copyright Jean-Paul Calderone.  See LICENSE file for details.

"""
Unit tests for the crop planning and scheduling module, L{cropplan}.
"""

from datetime import datetime

from zope.interface.verify import verifyObject

from twisted.trial.unittest import TestCase

from cropplan import (
    ITask, SeedFlats, DirectSeed, BedPreparation, Weed, Transplant, Harvest)


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



class SeedFlatsTests(TestCase, TaskTestsMixin):
    """
    Tests for L{SeedFlats}, representing a task for sowing seeds of a particular
    variety into flats.
    """
    def createTask(self):
        """
        Create a new L{SeedFlats} task using an arbitrary date, seed variety,
        and quantity.
        """
        return SeedFlats(datetime(2000, 6, 12, 8, 0, 0), object(), 50)



class DirectSeedTests(TestCase, TaskTestsMixin):
    """
    Tests for L{DirectSeed}, representing a task for sowing seeds of a
    particular variety directly into a bed.
    """
    def createTask(self):
        """
        Create a new L{DirectSeed} task using an arbitrary date, seed variety,
        and quantity.
        """
        return DirectSeed(datetime(2001, 7, 2, 9, 30, 0), object(), 10)



class BedPreparationTests(TestCase, TaskTestsMixin):
    """
    Tests for L{BedPreparation}, representing a task for preparing bed space for
    seeds of a particular variety (without specifying the details of that
    preparation; it may be amending, weeding, etc).
    """
    def createTask(self):
        """
        Create a new L{BedPreparation} task using an arbitrary date, seed
        variety, and quantity.
        """
        return BedPreparation(datetime(2002, 5, 25, 10, 15, 0), object(), 25)



class WeedTests(TestCase, TaskTestsMixin):
    """
    Tests for L{Weed}, representing a task for weeding bed space already planted
    in a particular variety.
    """
    def createTask(self):
        """
        Create a new L{Weed} task using an arbitrary date, seed variety, and
        quantity.
        """
        return Weed(datetime(2003, 8, 15, 11, 0, 0), object(), 50)



class TransplantTests(TestCase, TaskTestsMixin):
    """
    Tests for L{Transplant}, representing a task for transplanting seedlings of a
    particular variety from flats into bed space.
    """
    def createTask(self):
        """
        Create a new L{Transplant} task using an arbitrary date, seed variety,
        and quantity.
        """
        return Transplant(datetime(2004, 7, 1, 8, 0, 0), object(), 15)



class HarvestTests(TestCase, TaskTestsMixin):
    """
    Tests for L{Harvest}, representing a task for harvesting produce from bed
    space planted in particular variety.
    """
    def createTask(self):
        """
        Create a new L{Harvest} task using an arbitrary date, seed variety, and
        quantity.
        """
        return Harvest(datetime(2005, 9, 15, 9, 0, 0), object(), 25)
