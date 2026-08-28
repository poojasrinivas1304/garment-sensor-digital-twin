# Orientation-screening basis

The initial orientation study is a reduced-order strain-rosette calculation,
not a rotated three-dimensional FEBio simulation. It uses

`epsilon(theta) = exx cos(theta)^2 + eyy sin(theta)^2 + gamma_xy sin(theta) cos(theta)`

where `gamma_xy` is engineering shear strain. Projected textile strain is
multiplied by the scalar strain-transfer ratio from the 5 mm tapered
local-medium coupon.

The five imposed strain states are canonical basis cases selected to expose
horizontal, vertical, shear-sign and biaxial sensitivity. They are not measured
or simulated body movements. Their role is to eliminate redundant angle sets
before selected full-field simulations are built.

For reconstruction of all three in-plane strain components, at least three
nonredundant sensor axes are required. The D-optimal three-axis families on the
15-degree candidate grid are separated by 60 degrees, for example -60, 0 and
+60 degrees. Rotated equivalents contain the same orientation information.

Limitations:

- scalar transfer is assumed independent of angle;
- textile anisotropy is not yet included;
- bending and curvature are excluded;
- each calculation represents one spatial point;
- sensor-to-sensor manufacturing variability is excluded.
