"""Activates selection tool that picks a specific type of element.

Shift-Click:
Pick favorites from all available categories
"""
# pylint: disable=E0401,W0703,C0103
from collections import namedtuple

from pyrevit import revit, UI, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
my_config = script.get_config()


# somehow DB.BuiltInCategory.OST_Truss does not have a corresponding DB.Category
FREQUENTLY_SELECTED_CATEGORIES = [
    DB.BuiltInCategory.OST_Areas,
    DB.BuiltInCategory.OST_AreaTags,
    DB.BuiltInCategory.OST_AreaSchemeLines,
    DB.BuiltInCategory.OST_Columns,
    DB.BuiltInCategory.OST_StructuralColumns,
    DB.BuiltInCategory.OST_Dimensions,
    DB.BuiltInCategory.OST_Doors,
    DB.BuiltInCategory.OST_Floors,
    DB.BuiltInCategory.OST_StructuralFraming,
    DB.BuiltInCategory.OST_Furniture,
    DB.BuiltInCategory.OST_Grids,
    DB.BuiltInCategory.OST_Rooms,
    DB.BuiltInCategory.OST_RoomTags,
    DB.BuiltInCategory.OST_Truss,
    DB.BuiltInCategory.OST_Walls,
    DB.BuiltInCategory.OST_Windows,
    DB.BuiltInCategory.OST_Ceilings,
    DB.BuiltInCategory.OST_SectionBox,
    DB.BuiltInCategory.OST_ElevationMarks,
    DB.BuiltInCategory.OST_Parking
]


CategoryOption = namedtuple('CategoryOption', ['name', 'revit_cat'])


class PickByCategorySelectionFilter(UI.Selection.ISelectionFilter):
    """Selection filter implementation"""
    def __init__(self, category_opt):
        self.category_opt = category_opt

    def AllowElement(self, element):
        """Is element allowed to be selected?"""
        if element.Category \
                and self.category_opt.revit_cat.Id == element.Category.Id:
            return True
        else:
            return False

    def AllowReference(self, refer, point):  # pylint: disable=W0613
        """Not used for selection"""
        return False


class FSCategoryItem(forms.TemplateListItem):
    """Wrapper class for frequently selected category list item"""
    pass


def load_configs():
    """Load list of frequently selected categories from configs or defaults"""
    fscats = my_config.get_option('fscats', [])
    revit_cats = [revit.query.get_category(x)
                  for x in (fscats or FREQUENTLY_SELECTED_CATEGORIES)]
    return [x for x in revit_cats if x]


def save_configs(categories):
    """Save given list of categories as frequently selected"""
    my_config.fscats = [x.Name for x in categories]
    script.save_config()


def pick_by_category(category_opt):
    """Create selection handler that selects given category only"""
    try:
        selection = revit.get_selection()
        msfilter = PickByCategorySelectionFilter(category_opt)
        selection_list = revit.pick_rectangle(pick_filter=msfilter)
        filtered_list = []
        for element in selection_list:
            filtered_list.append(element.Id)
        selection.set_to(filtered_list)
    except Exception as err:
        logger.debug(err)


def reset_defaults(options):
    """Reset frequently selected categories to defaults"""
    defaults = [revit.query.get_category(x)
                for x in FREQUENTLY_SELECTED_CATEGORIES]
    default_names = [x.Name for x in defaults if x]
    for opt in options:
        if opt.name in default_names:
            opt.checked = True


def configure_fscats(prev_fscats):
    """Ask for users frequently selected categories"""
    all_cats = revit.doc.Settings.Categories
    prev_fscatnames = [x.Name for x in prev_fscats]
    fscats = forms.SelectFromList.show(
        sorted(
            [FSCategoryItem(x,
                            checked=x.Name in prev_fscatnames,
                            name_attr='Name')
             for x in all_cats],
            key=lambda x: x.name
            ),
        title='Select Favorite Categories',
        button_name='Apply',
        multiselect=True,
        resetfunc=reset_defaults
    )
    if fscats:
        save_configs(fscats)
    return fscats


source_categories = load_configs()
if __shiftclick__:  # pylint: disable=E0602
    source_categories = configure_fscats(source_categories)
    if not source_categories:
        script.exit()

# cleanup source categories
source_categories = filter(None, source_categories)
category_opts = \
    [CategoryOption(name=x.Name, revit_cat=x) for x in source_categories]
selected_category = \
    forms.CommandSwitchWindow.show(
        sorted([x.name for x in category_opts]),
        message='Pick only elements of type:'
    )

if selected_category:
    selected_category_opt = \
        next(x for x in category_opts if x.name == selected_category)
    logger.debug(selected_category_opt)
    pick_by_category(selected_category_opt)
