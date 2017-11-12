"""Aligns the section box of the current 3D view to selected face."""
from pyrevit.framework import Math
from pyrevit import revit, DB, UI


curview = revit.activeview

if isinstance(curview, DB.View3D) and curview.IsSectionBoxActive:
    try:
        ref = revit.uidoc.Selection.PickObject(UI.Selection.ObjectType.Face)
        el = revit.doc.GetElement(ref.ElementId)
        face = el.GetGeometryObjectFromReference(ref)
        box = curview.GetSectionBox()
        norm = face.ComputeNormal(DB.UV(0, 0)).Normalize()
        boxNormal = box.Transform.Basis[0].Normalize()
        angle = norm.AngleTo(boxNormal)
        axis = DB.XYZ(0, 0, 1.0)
        origin = DB.XYZ(box.Min.X + (box.Max.X - box.Min.X) / 2,
                        box.Min.Y + (box.Max.Y - box.Min.Y) / 2, 0.0)
        if norm.Y * boxNormal.X < 0:
            rotate = \
                DB.Transform.CreateRotationAtPoint(axis, Math.PI / 2 - angle,
                                                   origin)
        else:
            rotate = DB.Transform.CreateRotationAtPoint(axis,
                                                        angle,
                                                        origin)
        box.Transform = box.Transform.Multiply(rotate)
        with revit.Transaction('Orient Section Box to Face'):
            curview.SetSectionBox(box)
            revit.uidoc.RefreshActiveView()
    except Exception:
        pass
elif isinstance(curview, DB.View3D) and not curview.IsSectionBoxActive:
    UI.TaskDialog.Show("pyrevit",
                       "The section box for View3D isn't active.")
else:
    UI.TaskDialog.Show("pyrevit",
                       "You must be on a 3D view for this tool to work.")