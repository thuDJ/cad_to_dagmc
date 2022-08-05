from vertices_to_h5m import vertices_to_h5m
from pathlib import Path
import math


from cadquery import importers
from OCP.GCPnts import GCPnts_QuasiUniformDeflection

# from cadquery.occ_impl import shapes
import OCP
import cadquery as cq
from vertices_to_h5m import vertices_to_h5m
from OCP.TopLoc import TopLoc_Location
from OCP.BRep import BRep_Tool
from OCP.TopAbs import TopAbs_Orientation


def load_stp_file(filename: str, scale_factor: float = 1.0, auto_merge=True):
    """Loads a stp file and makes the 3D solid and wires available for use.
    Args:
        filename: the filename used to save the html graph.
        scale_factor: a scaling factor to apply to the geometry that can be
            used to increase the size or decrease the size of the geometry.
            Useful when converting the geometry to cm for use in neutronics
            simulations.
        auto_merge: whether or not to merge the surfaces. This defaults to True
            as merged surfaces are needed to avoid overlapping meshes in some
            cases. More details on the merging process in the DAGMC docs
            https://svalinn.github.io/DAGMC/usersguide/cubit_basics.html
    Returns:
        CadQuery.solid, CadQuery.Wires: solid and wires belonging to the object
    """

    part = importers.importStep(str(filename)).val()

    if scale_factor == 1:
        scaled_part = part
    else:
        scaled_part = part.scale(scale_factor)

    solid = scaled_part

    if auto_merge:
        solid = merge_surfaces(solid)

    return solid


def merge_surfaces(geometry):
    """Merges surfaces in the geometry that are the same"""

    solids = geometry.Solids()

    bldr = OCP.BOPAlgo.BOPAlgo_Splitter()

    if len(solids) == 1:
        # merged_solid = cq.Compound(solids)
        return solids[0]

    for solid in solids:
        # print(type(solid))
        # checks if solid is a compound as .val() is not needed for compounds
        if isinstance(solid, (cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Solid)):
            bldr.AddArgument(solid.wrapped)
        else:
            bldr.AddArgument(solid.val().wrapped)

    bldr.SetNonDestructive(True)

    bldr.Perform()

    bldr.Images()

    merged_solid = cq.Compound(bldr.Shape())

    return merged_solid


def tessellate(parts, tolerance: float = 0.1, angularTolerance: float = 0.1):
    """Creates a mesh / faceting / tessellation of the surface"""

    parts.mesh(tolerance, angularTolerance)

    offset = 0

    vertices: List[Vector] = []
    triangles = {}
    
    for f in s.Faces():
        
        loc = TopLoc_Location()
        poly = BRep_Tool.Triangulation_s(f.wrapped, loc)
        Trsf = loc.Transformation()

        reverse = (
            True
            if f.wrapped.Orientation() == TopAbs_Orientation.TopAbs_REVERSED
            else False
        )

        # add vertices
        face_verticles = [
            (v.X(), v.Y(), v.Z())
            for v in (v.Transformed(Trsf) for v in poly.Nodes())
        ]
        vertices += face_verticles

        face_triangles = [
            (
                t.Value(1) + offset - 1,
                t.Value(3) + offset - 1,
                t.Value(2) + offset - 1,
            )
            if reverse
            else (
                t.Value(1) + offset - 1,
                t.Value(2) + offset - 1,
                t.Value(3) + offset - 1,
            )
            for t in poly.Triangles()
        ]
        triangles[f.hashCode()] = face_triangles

        # solid_verticles

        offset += poly.NbNodes()

    list_of_triangles_per_solid=[]
    for s in parts.Solids():
        triangles_on_solid = []
        for f in s.Faces():
            triangles_on_solid.append(triangles[f.hashCode()])
        list_of_triangles_per_solid.append(triangles_on_solid)

    return vertices, list_of_triangles_per_solid
