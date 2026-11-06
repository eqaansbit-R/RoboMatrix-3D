# RoboMatrix 3D - Kinematics Visualizer

**Developed by Zainab & Co.Robotics**

## Project Overview

RoboMatrix 3D is an interactive desktop application for exploring rigid-body orientation and position in three dimensions. Adjust the pose with live controls and visualize the resulting coordinate frame and mathematical telemetry.

## Core Features

- **6-DoF pose controls:** Roll, pitch, and yaw sliders from −180° to +180°, plus X, Y, and Z translation sliders from −3.0 to +3.0 units.
- **NumPy matrix engine:** Computes the SO(3) rotation matrix using the Z-Y-X Tait–Bryan convention and combines it with translation in a 4×4 SE(3) homogeneous transformation matrix.
- **Exponential coordinates:** Displays the rotation vector, *ωθ*, using axis-angle extraction, including handling for identity and near-180° rotations.
- **Interactive 3D viewport:** PyOpenGL renders the RGB coordinate frame and updates it as the pose controls change.
- **Live SHA-256 signature:** Displays a digest computed from the transformation matrix and project string. This is a deterministic hash—not encryption or keyed authentication.
- **Quick reset:** Return all six controls and the visualized pose to zero.

## Tech Stack

- **Python**
- **PyQt5** — desktop interface and controls
- **PyOpenGL** — 3D viewport rendering
- **NumPy** — rotation and transformation calculations
- **hashlib** — SHA-256 digest generation

## Launch

Install the required packages, then run:

```bash
python visualizer.py