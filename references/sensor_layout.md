# Ten-sensor garment layout

Sources: manuscript Figure 2 and researcher-supplied photograph `IMG_8299.HEIC`,
reviewed on 2026-08-28. Figure 2 numbering is the canonical numbering for every
simulation, result table and future manuscript revision. The earlier Table 1
mapping is superseded because it conflicts with the visible geometry. The
drawing and worn-garment photograph are not dimensioned CAD; consequently the
current coordinates and angles remain normalized until a flat photograph with a
ruler is supplied.

| Sensor | Side | Region | Qualitative long-axis orientation |
|---|---|---|---|
| 1 | Front | upper left chest | diagonal |
| 2 | Front | upper right chest | diagonal, mirrored to 1 |
| 3 | Front | upper centre chest | vertical |
| 4 | Front | central torso | horizontal |
| 5 | Front | lower left torso | steep diagonal |
| 6 | Front | lower right torso | steep diagonal, mirrored to 5 |
| 7 | Front | lower centre torso | vertical |
| 8 | Back | upper centre | vertical |
| 9 | Back | left mid/lower back | diagonal |
| 10 | Back | right mid/lower back | diagonal, mirrored to 9 |

Use image-relative left and right in geometric files until anatomical-side
labels are verified. This avoids introducing a second ambiguity between the
wearer's side and the viewer's side.

All ten sensors are depicted as rectangular conductive strips with copper end
pads. Before building a full garment finite-element model, record for every
sensor: centre coordinates on a body/garment reference surface, long-axis angle,
active length and width, layer thicknesses, pad dimensions, and bonding area.

## Modelling consequence

The arrangement is suitable for an orientation/placement study: compare each
sensor's axial strain, transverse strain, bending, and strain-transfer ratio
during a library of upper-body motions. The strongest simulation-only paper is
not merely a ten-channel forward model; it is an optimization and uncertainty
study showing which placements remain informative under body-shape, garment-fit,
material, and motion variability.
