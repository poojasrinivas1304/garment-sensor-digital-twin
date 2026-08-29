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
| Resolved sensors | S3, S8 and S9 local meshes | Test whether transferred full-garment deformation retains sign and magnitude |

The case manifest indexes **206 simulation cases** and maps each reported case
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

These conclusions are an existence proof for one garment geometry, canonical
sensor layout and prescribed motion. They should not be generalized to other
garments, wearers or movements without matched analyses.

---

## Reproducibility Archive

The complete frozen bundle is attached to repository release **v1.0.0** as:

```text
Supplementary_Data_1_reproducibility.zip
```

Archive contents:

```text
Supplementary_Data_1_reproducibility/
├── README.md
├── model/          # FEBio .feb inputs and model metadata
├── references/     # Material basis and sensor-layout records
├── results/        # JSON/CSV outputs, case manifest and audit tables
└── scripts/        # Model generation, execution, post-processing and plots
```

The archive contains **731 files**. Its SHA-256 digest is:

```text
8144ca536f1cab21a346b4941ef285ddca2d43d4f6cc94c40e01efb251c317ba
```

Large raw solver logs and FEBio plot files are not included in the compact
bundle. They are retained by the authors and are available on reasonable
request.

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

After extracting the v1.0.0 archive, the principal deterministic drivers are:

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
python3 scripts/audit_taper_mesh_quality.py
python3 scripts/build_reproducibility_tables.py
```

Each simulation driver writes the exact FEBio input before execution and
retains model metadata and processed JSON/CSV output. The machine-readable case
manifest is the authoritative map between reported values and model files.

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

The repository is private during manuscript review. The reproducibility archive
and retained solver records are available from the corresponding authors on
reasonable request. Repository access may be opened after publication.

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
