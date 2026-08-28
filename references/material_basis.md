# Material basis and evidence limits

## Important limitation

The exact tensile curves of the polyester shirt, Luocute 95A backing filament,
and graphene-based conductive TPU filament used in the T-shirt have not been
measured. A unique constitutive calibration is therefore impossible. The values
below define sensitivity cases, not material identification.

## Polyester athletic textile: product identified, mechanics uncalibrated

The garment is the white shirt from the **Zoofly men's three-pack quick-dry
athletic T-shirt**, size XL, Amazon ASIN `B0D63CXLBR`, style `YYHFD9025`.
Product records describe it as a lightweight polyester, regular-fit, crew-neck
athletic shirt. The listing does not give an XL pattern drawing, fiber blend
percentage, knit construction, areal density or directional tensile curves.
Product link: https://www.amazon.ae/dp/B0D63CXLBR

The earlier manuscript description of the shirt as nylon must therefore be
corrected to polyester unless the physical care label provides contradictory
composition data. A photograph of that label should be retained as the primary
material record.

- Legacy nominal effective modulus used in completed screens: 0.24 MPa.
- Legacy sensitivity bracket: 0.10-5.0 MPa.
- Legacy Poisson ratio: 0.35.

These constants were originally borrowed from a nylon/elastane sportswear
analogue and are **not a literature calibration for this polyester product**.
They are retained only so completed numerical workflow screens remain
reproducible. Quantitative textile claims must use measured course/wale/bias
curves from the actual shirt.

The garment fabric must ultimately be represented by an anisotropic membrane or
shell law fitted in wale, course and shear directions. The present isotropic
solid and illustrative two-fiber variants are only workflow benchmarks.

The initial global extra-fine mesh (61,440 elements) developed local negative Jacobians at the abrupt patch ends and was computationally inefficient. Final verification should use local refinement at the patch edges rather than uniform global refinement.

## Non-conductive 95A TPU backing: identified product

The backing product is **Luocute white flexible TPU filament**, Amazon ASIN
`B0D5MMNBRY`. The seller lists 1.75 +/- 0.03 mm diameter, Shore 95A hardness,
200-220 deg C nozzle temperature and 60-80 deg C bed temperature:
https://www.amazon.ae/Luocute-Filament-Deformation-Mechanical-Rewinding/dp/B0D5MMNBRY

The listing does not provide a tensile curve, initial tangent modulus, Poisson
ratio, viscoelastic data, or printed-build anisotropy. Product identification
therefore improves provenance but does not justify a unique constitutive law.

- Nominal modulus: 48.4 MPa from an Ultrafuse TPU 95A technical data sheet (ISO 527, printed material): https://www.printam3d.ro/media/productattachment/0/2292/UltrafuseTPU95ATDSENv10.pdf
- Low case: 31.4 MPa, reported for printed Filaflex 95A.
- High case: 67 MPa, reported for printed Ultimaker TPU 95A.
- Supporting comparative study: https://www.mdpi.com/2073-4360/13/20/3551

These products remain hardness-matched mechanical analogues, not measurements
of the Luocute material itself.

## Conductive TPU: identified product

The sensing filament is **Graphene 3D Lab Conductive Flexible TPU**, 1.75 mm.
The retailer reports Shore 90A hardness and volume resistivity below
1.25 ohm-cm:
https://filament2print.com/en/conductive/785-graphene-flexible-conductive-tpu.html

The product page does not provide the printed tensile curve or a resistance-
strain-hysteresis dataset. Its stated bulk resistivity is useful for an order-of-
magnitude consistency check, but it cannot calibrate piezoresistivity.

- Low modulus: 12 MPa, reported for Palmiga PI-ETPU 95-250 in a review of conductive extrusion filaments: https://pmc.ncbi.nlm.nih.gov/articles/PMC11057547/
- High modulus: 90 MPa from the Conductive Filaflex 92A manufacturer technical data sheet: https://filamentworld.de/fact-sheets/Recreus_Filaflex-Conductive_92A_Datenblatt_EN.pdf
- Nominal screening value: 45 MPa, used only as a midpoint-scale case because
  the identified commercial filament has no published modulus on the supplied
  product page.

The same review shows that conductive TPU formulations span different filler
systems and resistivities. Even with the product now identified, the electrical
model cannot be calibrated responsibly until its resistance-strain curve is
available.

## Electrical response

The current postprocessor uses

`R/R0 = (1 + strain)^2 exp(beta strain)`

with beta = 4 solely to verify data transfer from FEBio to Python. This is not a calibrated law. Commercial conductive TPU can show positive, negative, rate-dependent and hysteretic responses; beta must not be used for paper claims.

For the current 80 x 15 x 0.6 mm conductive strip, the advertised bulk
resistivity implies an ideal homogeneous resistance below about 111 ohm
(`R = rho L/A`). This is not a prediction of the printed sensor's baseline
resistance: raster direction, voids, thermal history, copper interfaces and
contact resistance are absent. A measured or independently published printed
coupon curve is still required for quantitative voltage/resistance claims.
