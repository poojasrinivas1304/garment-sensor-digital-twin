# Multiscale Simulation of Strain Transfer in 3D-Printed TPU Smart Garments

> FEBio models, Python analysis code and reproducibility records accompanying
> the manuscript *Full-garment mechanics can reverse reduced-model strain
> predictions in directly printed TPU smart garments*.

---

## Overview

This repository contains the frozen computational record for a multiscale
study of strain transfer into directly printed conductive-TPU sensors on a
garment. The workflow connects three model scales:

1. **Coupon scale:** a textile, nonconductive-TPU backing and conductive-TPU
   sensing layer are resolved as a bonded three-layer solid.
2. **Garment scale:** a shell garment interacts with a prescribed torso and
   upper-ring movement through large-deformation contact.
3. **Sensor scale:** garment deformation gradients are transferred to resolved
   three-dimensional sensor submodels.

The study is entirely computational. Material properties are explicit,
uncalibrated modelling assumptions or sensitivity brackets; the repository
does not provide an experimentally calibrated electrical resistance law.

---

## Study Design

| Stage | Main variables | Primary purpose |
|---|---|---|
| Coupon geometry screen | Sensor length, width and layer thickness | Identify geometric strain-transfer trends |
| Edge regularization | Abrupt, 5 mm and 10 mm tapers | Reduce endpoint singularity and compare transfer |
| Mesh audit | Global and locally refined meshes | Quantify numerical sensitivity and taper-region quality |
| Material screen | Textile and TPU constitutive brackets | Test dependence on provisional material assumptions |
| Orientation screen | Sensor angle under canonical finite strain states | Compare reduced homogeneous-field predictions |
| Garment mechanics | Contact, no-contact and reduced controls | Separate garment kinematics from contact effects |
| Resolved sensors | S3/S9 local meshes and spatial boundary mapping | Test whether transferred full-garment deformation retains sign and magnitude |

The case manifest indexes **214 retained simulation cases** and maps each reported case
to its FEBio input, metadata, termination record and processed output.

---

## Main Computational Findings

- Coupon-scale strain transfer depends strongly on printed length, width and
  layer thickness, and the screened factors are not strictly additive.
- A finite printed-edge taper changes the endpoint strain-transfer estimate;
  the 10 mm taper produced the largest value among the tested taper lengths.
- The reduced homogeneous-field model predicts tensile response for the
  center-front and center-back sensors, whereas the matched garment-contact
  model predicts compression for the adopted geometry and movement field.
- Contact strengthens the compressive response at S3/S8, but garment-scale
  kinematics already reverse the reduced-model sign in the matched no-contact
  control.
- The same resolved-sensor sign was obtained on all three tested local meshes;
  this is a limited consistency result, not proof of asymptotic convergence or
  experimental validation.
- A spatial shell-node-derived boundary map retained the four tested S3/S9
  signs but increased the small no-contact S9 magnitude by more than threefold.
- A regularized in-plane mesh sequence terminated normally at all three levels
  and improved taper-region element quality, but its endpoint/path fine-grid
  GCIs of 14.1%/4.19% do not establish full 3D convergence.
- Augmented-Lagrangian enforcement completed for the frictionless contact pair;
  a new nonzero-friction fitted trial stagnated and was excluded before motion.

These conclusions are an existence proof for one garment geometry, canonical
sensor layout and prescribed motion. They should not be generalized to other
garments, wearers or movements without matched analyses.

---

## Reproducibility Archive

This paper-only archive contains the computational cases and utilities that
support the manuscript and its supplementary information. Invalid exploratory
60-mm cases, superseded plot variants and manuscript-formatting utilities have
been removed. Every retained numerical claim is mapped in
`claim_to_file_manifest.csv`; every deliberate exclusion is recorded in
`excluded_files.csv`.

Archive contents:

```text
paper_reproducibility_archive/
├── README.md
├── claim_to_file_manifest.csv
├── excluded_files.csv
├── file_inventory_sha256.csv
├── figures/        # Fourteen final manuscript figure files
├── model/          # 214 FEBio inputs + 214 matched metadata records
├── references/     # Material basis and sensor-layout records
├── results/        # Frozen outputs, audit tables and four plot-source logs
└── scripts/        # Retained generation, execution, processing and final plots
```

The archive contains **214 indexed simulation cases**. Of these, 179 reached
normal termination and 35 are retained failed or interrupted numerical trials.
The latter support bounded solver diagnostics only; no physical response is
inferred from them. The `model/` directory therefore contains 428 files: one
FEBio input and one metadata record per indexed case.
The remaining files are processed outputs, aggregate tables, reference records
and analysis utilities rather than additional simulations.

| Content | Files | Interpretation |
|---|---:|---|
| FEBio inputs | 214 | Indexed normal and diagnostic simulation cases |
| Model metadata | 214 | One record per indexed case |
| Results | 244 | JSON/CSV outputs plus five required solver logs |
| Scripts | 51 | Generation, execution, processing, audits and final plots |
| References | 5 | Material, layout and prospective-test records |
| Final figures | 14 | Exact JPEG files used by the manuscript |
| Root documentation/manifests | 4 | README and three machine-readable audit files |

The archive contains 746 files in total. This is an artifact count, not a
simulation count. `file_inventory_sha256.csv` records the size and SHA-256
digest of every other file in the archive.

Five solver logs required to reconstruct manuscript figures or the interrupted
contact diagnostic are
included. The other raw solver logs and FEBio plot files exceed the practical
size of the review bundle; their termination and diagnostic summaries are
frozen in `case_manifest.csv`, and the raw files are retained by the authors
for provision on reasonable request.

---

## Software Environment

The audited calculations used:

- FEBio 4.13.0
- macOS 15.3.2 on arm64
- Python 3.14.5
- NumPy 2.4.6
- Matplotlib 3.10.9

Users on another platform must update the FEBio executable path in the driver
scripts without changing the model parameters.

---

## Reproducing the Analysis

After extracting the archive, the principal deterministic drivers are:

```bash
python3 scripts/run_geometry_screening.py
python3 scripts/run_taper_screening.py
python3 scripts/run_material_sensitivity.py
python3 scripts/run_orientation_screening.py
python3 scripts/run_textile_anisotropy.py
python3 scripts/run_garment_kinematic_screen.py
python3 scripts/run_garment_submodels.py
python3 scripts/run_contact_aware_sensor_submodels.py
python3 scripts/run_garment_contact_sensitivity.py
python3 scripts/run_matched_garment_controls.py
python3 scripts/run_relative_F_sensor_mesh.py
python3 scripts/run_spatial_boundary_transfer.py
python3 scripts/run_quality_mesh_convergence.py
python3 scripts/build_augmented_contact_continuation_audit.py
python3 scripts/audit_taper_mesh_quality.py
python3 scripts/build_reproducibility_tables.py
```

Each simulation driver writes the exact FEBio input before execution and
retains model metadata and processed JSON/CSV output. The machine-readable case
manifest maps the 214 indexed cases to their model files. The separate
claim-to-file manifest maps manuscript figures, tables and supplementary
sections to the relevant data and scripts.

Create the output directory and use a noninteractive Matplotlib backend when
regenerating figures:

```bash
mkdir -p figures
export MPLBACKEND=Agg
```

The final submitted visual variants for Figures 10--14 are produced by:

```bash
python3 scripts/plot_contact_verification_publication_v2.py
python3 scripts/plot_matched_garment_controls_publication.py
python3 scripts/plot_full_garment_reversal_field_publication.py
python3 scripts/plot_relative_F_sensor_mesh_trajectory.py
python3 scripts/plot_numerical_remediation.py
```

---

## Important Limitations

- Constitutive parameters have not been calibrated against tensile tests of
  the specific shirt or printed filaments.
- The garment loading is prescribed rather than obtained from motion capture.
- The torso is idealized, and the study evaluates one garment geometry and one
  canonical ten-sensor layout.
- The sensor model predicts mechanical strain, not resistance, gauge factor or
  biosignal-classification performance.
- Mesh studies establish tested-mesh consistency only where stated; they do
  not justify universal mesh-independence claims.

---

## Data Access

The repository is private during manuscript review. This paper-only archive and
the retained full solver records are available from the corresponding authors
on reasonable request. Repository access may be opened after publication.

---

## Citation

If you use these models or scripts, please cite the associated manuscript. The
final journal citation and DOI will be added after publication.

```bibtex
@article{gurram_garment_sensor_digital_twin,
  title   = {Full-garment mechanics can reverse reduced-model strain predictions
             in directly printed TPU smart garments},
  author  = {Gurram, Pooja and Elgendi, Mohamed},
  journal = {To be updated},
  year    = {2026},
  doi     = {To be updated}
}
```

---

## Funding

This work was supported by Khalifa University under grant FSU-2025-001 and by
the Healthcare Engineering Innovation Group, Khalifa University of Science
and Technology.

---

## Authors

- **Pooja Gurram** — sensor-system development, computational workflow,
  analysis, visualization and manuscript preparation
- **Mohamed Elgendi** — supervision, conceptualization, interpretation and
  critical manuscript revision
