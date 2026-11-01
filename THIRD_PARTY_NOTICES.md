# Third-party sources and attribution

This repository's orchestration scripts and VINS-Fusion patch are distributed under GNU GPL v3; see LICENSE. Third-party software, images and datasets retain their own terms.

- **VINS-Fusion**, HKUST Aerial Robotics Group, fixed commit `be55a937a57436548ddfb1bd324bc1e9a9e828e0`: https://github.com/HKUST-Aerial-Robotics/VINS-Fusion . Upstream is GPL v3. Source and copyright notices are retained when scripts/build.sh clones it; the complete changes are in patches/vins-fusion.patch. This project is an independent reproduction, not the official upstream repository.
- **Ceres Solver 1.14.0**: https://github.com/ceres-solver/ceres-solver/tree/1.14.0 . Its BSD license is reproduced in docs/licenses/Ceres-1.14.0.txt and in the bundled source tarball. The source tarball is checksum-pinned in the Dockerfile.
- **Ubuntu, ROS Kinetic, OpenCV, Eigen, SuiteSparse and other image packages** retain their respective licenses. The Dockerfile pins the OS/ROS base image digest; environment/final_packages.txt records the installed packages, and environment/BUILD_NOTES.md records their build sources and versions. Source rebuild instructions are provided in the README.
- **EuRoC MAV Dataset**, Michael Burri et al., ETH Zurich: https://projects.asl.ethz.ch/datasets/euroc-mav/ ; archive DOI https://doi.org/10.3929/ethz-b-000690084 ; paper “The EuRoC micro aerial vehicle datasets”, IJRR 2016, https://doi.org/10.1177/0278364915620033 . Input data are downloaded separately. Release map images and matched-image examples derive from this dataset; the dataset's terms are independent of the software license. Data provenance and integrity checks are recorded in docs/data-provenance.json.

The ETH archive submission/use terms are preserved in docs/licenses/EuRoC-archive-license.txt; end-user data licensing is determined by the official dataset record, not by this repository's GPL software license.

The official EuRoC record states **In Copyright - Non-Commercial Use Permitted**, with rights statement http://rightsstatements.org/page/InC-NC/1.0/ . The record is preserved in docs/licenses/EuRoC-rights-record.json. Dataset-derived map images, matching examples and recorded image topics are teaching/research materials subject to those data terms; they are not relicensed as GPL software.
