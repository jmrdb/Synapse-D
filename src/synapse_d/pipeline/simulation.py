"""Brain simulation module — TVB integration.

Calls the TVB worker container to run brain network simulation
from a structural connectivity matrix. Produces simulated EEG
and functional connectivity (FC) matrix.

The TVB worker is GPL-licensed and runs in a separate Docker container.
Communication is via REST API only — no code sharing with Synapse-D.

Key output for IR demo:
- Structural Connectivity (SC, input) vs Functional Connectivity (FC, output)
- "This patient's brain wiring produces this activity pattern"
"""

from dataclasses import dataclass, field

import numpy as np
import requests
from loguru import logger

from synapse_d.config import settings


@dataclass
class SimulationResult:
    """Brain simulation result.

    Attributes:
        success: Whether simulation completed.
        n_regions: Number of brain regions.
        eeg_timepoints: Number of EEG time points.
        fc_matrix: Functional connectivity matrix (NxN correlations).
        fc_mean_correlation: Mean off-diagonal FC correlation.
        sc_fc_correlation: Correlation between SC and FC matrices.
        elapsed_seconds: Simulation time.
        model: Neural mass model used.
        errors: List of errors.
    """

    success: bool = False
    n_regions: int = 0
    eeg_timepoints: int = 0
    fc_matrix: list[list[float]] = field(default_factory=list)
    fc_mean_correlation: float = 0.0
    sc_fc_correlation: float = 0.0
    elapsed_seconds: float = 0.0
    model: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "n_regions": self.n_regions,
            "eeg_timepoints": self.eeg_timepoints,
            "fc_matrix": self.fc_matrix,
            "fc_mean_correlation": round(self.fc_mean_correlation, 4),
            "sc_fc_correlation": round(self.sc_fc_correlation, 4),
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "model": self.model,
            "errors": self.errors,
        }


def run_brain_simulation(
    connectivity_matrix: list[list[float]],
    simulation_length_ms: float = 10000.0,
    model: str = "generic2d",
    subject_id: str = "",
) -> SimulationResult:
    """Run brain simulation via TVB worker.

    Args:
        connectivity_matrix: NxN structural connectivity matrix.
        simulation_length_ms: Simulation length in ms (default 10s).
        model: Neural mass model ("generic2d" or "wilson_cowan").
        subject_id: For logging.

    Returns:
        SimulationResult with FC matrix and SC-FC correlation.
    """
    result = SimulationResult()
    tvb_url = settings.tvb_worker_url

    logger.info(f"[{subject_id}] Starting brain simulation "
                f"({len(connectivity_matrix)}x{len(connectivity_matrix)}, "
                f"{simulation_length_ms}ms, {model})")

    try:
        resp = requests.post(
            f"{tvb_url}/simulate",
            json={
                "weights": connectivity_matrix,
                "simulation_length_ms": simulation_length_ms,
                "model": model,
            },
            timeout=300,
        )

        if resp.status_code != 200:
            try:
                error = resp.json().get("detail", resp.text)[:200]
            except (ValueError, KeyError):
                error = resp.text[:200]
            result.errors.append(f"TVB simulation failed: {error}")
            logger.error(f"[{subject_id}] TVB error: {error}")
            return result

        data = resp.json()
        result.success = True
        result.n_regions = data["n_regions"]
        result.eeg_timepoints = data["eeg_timepoints"]
        result.fc_matrix = data["functional_connectivity"]
        result.fc_mean_correlation = data["fc_mean_correlation"]
        result.elapsed_seconds = data["elapsed_seconds"]
        result.model = data["model_used"]

        # Compute SC-FC correlation (structure-function relationship)
        sc = np.array(connectivity_matrix)
        fc = np.array(data["functional_connectivity"])
        n = sc.shape[0]
        sc_upper = sc[np.triu_indices(n, k=1)]
        fc_upper = fc[np.triu_indices(n, k=1)]
        if len(sc_upper) > 0 and np.std(sc_upper) > 0 and np.std(fc_upper) > 0:
            result.sc_fc_correlation = float(np.corrcoef(sc_upper, fc_upper)[0, 1])

        logger.info(f"[{subject_id}] Simulation complete: "
                    f"{result.eeg_timepoints} EEG points, "
                    f"FC corr={result.fc_mean_correlation:.3f}, "
                    f"SC-FC r={result.sc_fc_correlation:.3f}, "
                    f"{result.elapsed_seconds}s")

    except requests.exceptions.ConnectionError:
        result.errors.append("TVB worker not available (connection refused)")
        logger.warning(f"[{subject_id}] TVB worker not reachable at {tvb_url}")
    except requests.exceptions.Timeout:
        result.errors.append("TVB simulation timed out (>5min)")
        logger.error(f"[{subject_id}] TVB simulation timeout")
    except Exception as e:
        result.errors.append(f"TVB simulation error: {e}")
        logger.error(f"[{subject_id}] TVB error: {e}")

    return result
