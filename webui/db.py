from axiom.item import Item
from axiom.attributes import text, integer

class Crop(Item):
    name = text()
    picture = text()
    description = text()

    yield_lbs_per_bed_foot = integer()
    rows_per_bed = integer()
    harvest_weeks = integer()
    row_feet_per_oz_seed = integer()
    in_row_spacing = integer()
