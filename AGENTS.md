# Reproducing this repository

Run the complete experiment with `bash scripts/reproduce.sh` from the repository root. This creates a new MH01 map, restarts the nodes, localizes MH02 against that map, and verifies actual ROS messages. Keep the run active until its summary records a terminal result.

1. For a Windows host or a failed environment check, read [platform setup](docs/platforms.md). Execute Linux commands inside the x86_64 WSL2 distribution. Completion: the doctor stage passes with Docker daemon access.
2. Run the full entrypoint. Follow `results/<run-id>/summary.json` and its stage logs. Completion: fresh MH01 map validation and the new MH02 verification both pass, and owned containers have stopped.
3. Report the new summary path, PnP/alignment evidence, continuous-pose evidence and result images. State the platform actually tested.

`reference_results/` and the published map are historical examples. A new reproduction is evidenced by the newly created run ID and its newly built map, not by a reference report. Ground truth is used only by post-run evaluation. Preserve the PnP, alignment and pose checks when diagnosing failures.

For download failures, permissions, timeouts or slow CPUs, read [troubleshooting](docs/troubleshooting.md). Preserve logs and partial downloads; resolve the recorded cause and start with a new run ID. Existing maps/results are retained. An administrator prompt, reboot or unavailable network requires a specific explanation to the user; it does not constitute a successful experiment.

Implementation: ROS Kinetic/Python 2 runs inside the pinned Docker image; host tools use Python >=3.8 standard library. Upstream VINS-Fusion is fetched at the commit fixed in `scripts/build.sh`, with the tracked patch applied. Algorithm changes are outside the default reproduction task.
