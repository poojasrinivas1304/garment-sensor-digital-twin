# Prospective targeted experiment (not yet performed)

## Purpose

This protocol is the minimum physical check proposed after the computational
screen. It is not part of the present numerical evidence and must not be cited
as completed validation. Its two aims are to (1) measure whether the printed
gauge produces a repeatable electrical response and (2) test the predicted
S3-compression/S9-tension contrast under one reproducible garment motion.

## Feasibility gate

1. Record the UTM load-cell capacity, calibration date and smallest displayed
   force increment.
2. Pull one unprinted shirt-fabric strip through 10% strain. The peak force
   should exceed 20 times the smallest force increment before UTM force data
   are treated quantitatively. If it does not, use a lower-capacity load cell;
   displacement and resistance may still be recorded, but force-based
   calibration must be deferred.
3. Confirm that the resistance meter resolves at least 0.1% of the unstrained
   sensor resistance at the intended sampling rate.

## A. Small coupon check

- Prepare three repeat specimens for an abrupt printed termination and three
  for the 10-mm taper, using the same shirt fabric, conductive TPU, backing
  TPU, raster direction, layer heights and temperatures as the garment.
- Record gauge length, width and printed thickness for every specimen.
- Use compliant tabs and a fixed initial gauge length. Photograph the unloaded
  setup with a scale.
- Precondition for five cycles from 0 to 5% nominal strain, then acquire three
  cycles from 0 to 10% at a fixed crosshead rate. Record crosshead
  displacement, force and resistance synchronously.
- Report all replicates, the mean and standard deviation of
  \(\Delta R/R_0\), loading/unloading hysteresis, drift after preconditioning
  and failure/slip observations. Do not fit an electrical constitutive law
  from fewer than three successful specimens per design.
- Primary test: whether the 10-mm taper changes mechanical/electrical response
  in the direction predicted by the numerical screen. This does not validate
  the garment-level sign reversal.

## B. Targeted garment sign check

- Instrument only S3 and S9 on one garment, because these are the two locations
  carried into the resolved submodels.
- Mount the garment on a dimensioned rigid torso or reproducible hanger/frame.
  Mark the top boundary and impose the same arm-raise surrogate displacement
  used by the model at 25% amplitude; document the displacement with a ruler
  or video scale.
- Record both resistances during ten repeated loading/unloading cycles after
  five preconditioning cycles. If practical, place two optical markers at each
  sensor terminal to obtain endpoint-centroid strain from video.
- Compare only response direction, repeatability and phase between S3 and S9.
  A resistance sign must not be equated to mechanical strain sign until the
  coupon test establishes the material-specific resistance--deformation
  relationship.

## Reporting rules

- Preserve raw time-series files and a specimen/case manifest.
- State exclusions before viewing the final comparison (electrode detachment,
  visible specimen slip, broken trace or missing synchronization).
- Do not describe agreement as model validation unless geometry, motion,
  material batch and boundary conditions match the corresponding simulation.
- Human-wearer testing is outside this minimal protocol and would require the
  applicable ethics and consent review before recruitment.
