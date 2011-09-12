"""
http://teltanefarm.com/garlic.html

75' softneck
25' hardneck

Softneck - 10-16 cloves per bulb
           8-10 bulbs per pound

Porcelain (hardneck) - 4-6 cloves per bulb
                       6-8 bulbs per pound
Racambole / Purple Stripe - 6-9 cloves per bulb
                            8-10 bulbs per pound


Softneck
========
75' x 3 rows x 2/ft spacing = 450 bulbs
450 / average(10, 16) / average(8, 10)

Inchelium
"""

from __future__ import division

SOFTNECK = {
    'clovesPerBulb': (10, 16),
    'bulbsPerPound': (8, 10),
    'rows': 3,
    'perFoot': 2,
    }

PORCELAIN = {
    'clovesPerBulb': (4, 6),
    'bulbsPerPound': (6, 8),
    'rows': 3,
    'perFoot': 2,
    }

PURPLE_STRIPED = RACAMBOLE = {
    'clovesPerBulb': (6, 9),
    'bulbsPerPound': (8, 10),
    'rows': 3,
    'perFoot': 2,
    }

GARLIC_DATA = {
    'Inchelium': SOFTNECK,
    'Rosewood': PORCELAIN,
    'Siberian Red': PURPLE_STRIPED,
    'Musik': PORCELAIN,
    }

PLANTING_DATA = {
    'Inchelium': 70,
    'Rosewood': 10,
    'Siberian Red': 10,
    'Musik': 10,
    }

def seedPoundsPerFoot((minClovesPerBulb, maxClovesPerBulb),
                      (minBulbsPerPound, maxBulbsPerPound),
                      rows, perFoot):
    neededCloves = rows * perFoot
    minNeeded = neededCloves / maxClovesPerBulb / maxBulbsPerPound
    maxNeeded = neededCloves / minClovesPerBulb / minBulbsPerPound
    return minNeeded, maxNeeded


def yieldPoundsPerFoot((minBulbsPerPound, maxBulbsPerPound),
                       rows, perFoot):
    seededCloves = rows * perFoot
    minYield = seededCloves / maxBulbsPerPound
    maxYield = seededCloves / minBulbsPerPound
    return minYield, maxYield


for variety, feet in PLANTING_DATA.iteritems():
    data = GARLIC_DATA[variety]
    minNeeded, maxNeeded = seedPoundsPerFoot(
        data['clovesPerBulb'], data['bulbsPerPound'],
        data['rows'], data['perFoot'])
    print '%(variety)s min %(min)0.2f max %(max)0.2f' % {
        'variety': variety, 'min': minNeeded * feet, 'max': maxNeeded * feet}
    print ' ' * 10, 'halfway %0.2f' % ((minNeeded + maxNeeded) / 2 * feet,)
    minYield, maxYield = yieldPoundsPerFoot(
        data['bulbsPerPound'],
        data['rows'], data['perFoot'])
    print ' ' * 10, 'yield min %0.2f max %0.2f' % (
        minYield * feet, maxYield * feet)


