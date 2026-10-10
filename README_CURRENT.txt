REVISION ADDENDUM - CURRENT MANUSCRIPT DOCUMENTATION
Manuscript ID: 1988369
Revision date: 10 October 2026

Current manuscript title:
Full-garment mechanics can reverse sensor-placement predictions in wearable
movement-monitoring devices: an in silico study

READ THIS FILE FIRST

PUBLIC ACCESS - CURRENT STATUS

The GitHub repository and release v1.1.0 are public and accessible without
signing in:
https://github.com/poojasrinivas1304/garment-sensor-digital-twin/releases/tag/v1.1.0

Download Supplementary_Data_1_reproducibility.zip attached to that release for
the revised manuscript data and code. The main-branch computational files and
automatically generated source-code archives represent the earlier package.
The original README's statement that access was private during review is
historical and is superseded by this public-access statement. This updated
repository addendum clarifies access without replacing either released ZIP
or changing computational data, existing inventories or legacy identifiers.
Additional large raw solver logs and FEBio plot files not included in the
release asset are available from the corresponding authors on reasonable
request.

This package retains every original computational file, the original README.md,
claim_to_file_manifest.csv and file_inventory_sha256.csv unchanged. The older
title and figure numbers in those documents are historical provenance, not the
current manuscript numbering. No model input, result, numerical value or legacy
case identifier was changed for this revision. The original ZIP is also retained
separately by the authors.

CURRENT DOCUMENTATION

- claim_to_file_manifest_revised.csv is the current manuscript claim index.
  Figure claims F1-F16 use the current figure numbers. Additional columns retain
  each legacy claim ID, location and scope note. Non-figure rows with embedded
  figure references are aligned too. The original prospective experiment
  protocol remains a reference document, not a nonexistent Supplementary S17.
- figure_number_mapping.csv maps all 16 current figures to the old numbering,
  manuscript asset names and retained archive figures. Current Figure 1 is the
  construction/mesh/coordinate-map visualization added during peer review; it
  was Figure 16 in the initial revision draft and had no original F1-F15 claim.
- file_inventory_revision_sha256.csv covers every file in this expanded package
  except itself. Its original/revision classification distinguishes retained
  computational provenance from revision additions. The original inventory is
  retained unmodified and still validates the original 807 listed files.
- revision_2026_10_09/figure_01_provenance.json records the new visualization's
  archived input dependencies, scripts, accepted assets and their SHA-256 hashes.

MATERIAL PROVENANCE

Material properties are uncalibrated nominal model inputs, informed by published
and manufacturer reference data where available. The coupon textile modulus is
an intentionally compliant workflow input, not a measurement of the identified
garment. The deterministic sensitivity brackets are not specimen-specific
uncertainty intervals. The historical machine-readable identifier
literature_nominal is retained for traceability; it does not imply that every
constant was literature-derived or experimentally calibrated. See revised
main-text Methods and Table 2, and Supplementary Section S2.

NEW FIGURE 1 ASSETS AND REPRODUCTION

Accepted assets are retained at:
revision_2026_10_09/figures/Figure_01_model_geometry.pdf
revision_2026_10_09/figures/Figure_01_model_geometry.png

Run from the extracted archive root:
python3 revision_2026_10_09/scripts/create_figure_01_model_geometry.py

Requires Python, NumPy and Matplotlib. Tested versions are recorded in the
provenance JSON. The script reads existing files in model/ and writes only
derivatives under revision_2026_10_09/generated/. It does not run FEBio or modify
accepted figures or computational records. The original workspace plotting
script is preserved as original_create_reviewer2_figure_refined.py; the portable
adaptation changes paths and reference comments, not plotting geometry.

Panels a and d contain explanatory construction/coordinate schematics; panels b
and c draw the actual archived undeformed input meshes. Terminal pads are not
separately meshed, sleeves and neckline are absent from the shell, and no strain
field or new simulation result is generated. The visualization is not physical
or electromechanical validation.

VERIFICATION

The expanded archive is checked for ZIP integrity, preservation of all original
file bytes, original inventory hashes, current figure coverage and existence of
the computational paths in the revised claim index. The portable visualization
is checked against the accepted raster asset. These checks do not constitute
a rerun or independent reproduction of the finite-element simulation results.
