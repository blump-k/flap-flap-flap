import math
from build123d import *

# The radius of the wheel will be set by the number of flaps needed
n_flaps = 69

# pinhole pitch calcs
pin_len = 3
ph_cl = 0.4
ph_sep = 1.2
ph_rad = (ph_cl + pin_len) / 2

ph_pitch = ph_sep + ph_rad * 2

# wheel outer radius set by circumference + wall thickness
wh_rad_ph_cen = ph_pitch * n_flaps / (2 * math.pi)
ph_wall_out = 2
wh_rad_out = wh_rad_ph_cen + ph_rad + ph_wall_out

# wheel inner diameter is set by motor shaft diameter
drive_shaft_diam = 5.0
drive_shaft_cl = 0.2

outer_radius = wh_rad_out
hole_radius = (drive_shaft_diam + drive_shaft_cl) / 2
wh_thickness = 3

drive_hub_radius = 10
spoke_wd = 6
ph_wall_in = 2

wh_rad_ph_in = wh_rad_ph_cen - ph_rad - ph_wall_in

with BuildPart() as wheel_blank:
    Cylinder(radius=outer_radius, height=wh_thickness)
    Hole(radius=hole_radius)

    # Polar array of holes cut through the disc
    with PolarLocations(radius=wh_rad_ph_cen, count=n_flaps):
        Hole(radius=ph_rad)

with BuildSketch(Plane.XY) as cutter:
    Circle(radius=wh_rad_ph_in)
    Rectangle(wh_rad_ph_in * 2, wh_rad_ph_in * 2, rotation=45, mode=Mode.SUBTRACT)
    Rectangle(wh_rad_ph_in * 2, spoke_wd, rotation=0, mode=Mode.ADD)
    Rectangle(spoke_wd, wh_rad_ph_in * 2, rotation=0, mode=Mode.ADD)
    Circle(radius=wh_rad_ph_in, mode=Mode.ADD)

extrude(cutter.sketch, amount=-wh_thickness, mode=Mode.SUBTRACT)

# Get the directory where this python script lisves
export_step(wheel_blank.part, "wheel_v0.step")

