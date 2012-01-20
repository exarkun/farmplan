# Copyright Jean-Paul Calderone.  See LICENSE file for details.

"""
Bazaar plugin for automatically writing out an updated iCalendar schedule.
"""

import sys, os, tempfile

from bzrlib import branch

from twisted.python.filepath import FilePath


def post_change_branch_tip(params):
    conf = params.branch.get_config()
    sys.stderr.write(str(conf) + '\n')
    if not conf.get_user_option('farm-schedule:enabled'):
        return
    destination = conf.get_user_option('farm-schedule:destination')
    destination = os.path.expanduser(destination)

    try:
        checkout = tempfile.mktemp()
        sys.stderr.write('Updating code...\n')
        make_importable(params.branch, checkout)
        sys.stderr.write('Writing schedule...\n')
        write_schedule(destination)
        sys.stderr.write('Done\n')
    finally:
        FilePath(checkout).remove()


def make_importable(branch, checkout):
    branch.create_checkout(to_location=checkout, lightweight=True)
    sys.path.append(checkout)
    return checkout


def write_schedule(destination):
    from cropplan import (
        __file__, load_crops, load_seeds, create_tasks, schedule_tasks,
        schedule_ical)

    HERE = FilePath(__file__).realpath().parent()
    CROP_PLAN = HERE.child('2012 Crop Plan.csv')
    CROP_VARIETIES = HERE.child('2012 Crop Plan - Varieties.csv')

    crops = load_crops(CROP_PLAN)
    sys.stderr.write('Loaded %d crops...\n' % (len(crops),))
    seeds = load_seeds(CROP_VARIETIES, crops)
    sys.stderr.write('Loaded %d seeds...\n' % (len(seeds),))
    tasks = create_tasks(crops, seeds)
    schedule = schedule_tasks(tasks)

    output = file(destination, 'w')
    stdout = sys.stdout
    try:
        sys.stdout = output
        schedule_ical(schedule)
    finally:
        sys.stdout = stdout


branch.Branch.hooks.install_named_hook(
    'post_change_branch_tip', post_change_branch_tip, 'deployment restart')
