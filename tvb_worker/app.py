"""TVB Worker — Brain Simulation REST API.

GPLv3-licensed TVB brain simulation engine wrapped in a REST API.
Runs in a separate Docker container to prevent GPL contamination
of the main Synapse-D codebase.

Endpoints:
    POST /simulate — Run brain network simulation
    GET  /health   — Health check

Input: Structural connectivity matrix (NxN)
Output: Simulated EEG time series + Functional Connectivity matrix
"""

import time

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="TVB Brain Simulation Worker",
    description="GPLv3 isolated brain simulation engine",
    version="0.1.0",
)


class SimulationRequest(BaseModel):
    """Input for brain simulation."""

    weights: list[list[float]]  # NxN structural connectivity matrix
    region_labels: list[str] | None = None
    simulation_length_ms: float = 10000.0  # 10 seconds default
    model: str = "generic2d"  # "generic2d" or "wilson_cowan"


class SimulationResponse(BaseModel):
    """Output from brain simulation."""

    success: bool
    n_regions: int
    simulation_length_ms: float
    model_used: str
    eeg_timepoints: int
    eeg_sample_rate_hz: float
    eeg_time_series: list[list[float]]  # (T, N) — EEG per region
    functional_connectivity: list[list[float]]  # (N, N) — FC matrix
    fc_mean_correlation: float
    elapsed_seconds: float


@app.get("/health")
def health():
    return {"status": "ok", "engine": "TVB", "license": "GPLv3"}


@app.post("/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest):
    """Run TVB brain network simulation.

    Takes a structural connectivity matrix and produces simulated
    brain activity (EEG time series) and functional connectivity.
    """
    start = time.time()

    try:
        weights = np.array(req.weights, dtype=np.float64)
        n = weights.shape[0]

        if weights.shape != (n, n):
            raise ValueError(f"Weight matrix must be square, got {weights.shape}")
        if n < 2:
            raise ValueError(f"Need at least 2 regions, got {n}")
        if n > 200:
            raise ValueError(f"Max 200 regions supported, got {n}")
        if weights.max() == 0:
            raise ValueError("All-zero connectivity matrix — no connections to simulate")

        # Normalize weights
        max_w = weights.max()
        if max_w > 0:
            weights = weights / max_w
        weights[np.isnan(weights)] = 0.0
        np.fill_diagonal(weights, 0.0)

        # Run TVB simulation
        eeg_ts, time_axis = _run_tvb_simulation(
            weights, n, req.simulation_length_ms, req.model
        )

        # Compute functional connectivity from simulated EEG
        fc = np.corrcoef(eeg_ts.T)  # (N, N)
        fc[np.isnan(fc)] = 0.0
        np.fill_diagonal(fc, 1.0)

        elapsed = time.time() - start

        # Downsample EEG for API response (max 1000 timepoints)
        if eeg_ts.shape[0] > 1000:
            step = eeg_ts.shape[0] // 1000
            eeg_ts = eeg_ts[::step]

        return SimulationResponse(
            success=True,
            n_regions=n,
            simulation_length_ms=req.simulation_length_ms,
            model_used=req.model,
            eeg_timepoints=eeg_ts.shape[0],
            eeg_sample_rate_hz=1000.0 / (time_axis[1] - time_axis[0]) if len(time_axis) > 1 else 0,
            eeg_time_series=eeg_ts.tolist(),
            functional_connectivity=fc.tolist(),
            fc_mean_correlation=float(fc[np.triu_indices(n, k=1)].mean()),
            elapsed_seconds=round(elapsed, 2),
        )

    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"TVB not installed: {e}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}\n{tb}")


def _run_tvb_simulation(
    weights: np.ndarray, n_regions: int,
    sim_length_ms: float, model_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Execute TVB brain simulation.

    Args:
        weights: NxN normalized connectivity matrix.
        n_regions: Number of brain regions.
        sim_length_ms: Simulation length in milliseconds.
        model_name: Neural mass model ("generic2d" or "wilson_cowan").

    Returns:
        Tuple of (eeg_timeseries (T, N), time_axis (T,)).
    """
    from tvb.simulator import lab

    # Build TVB Connectivity object
    conn = lab.connectivity.Connectivity()
    conn.weights = weights
    conn.tract_lengths = np.ones((n_regions, n_regions)) * 10.0
    conn.region_labels = np.array([f"r{i}" for i in range(n_regions)])
    conn.centres = np.zeros((n_regions, 3))
    conn.hemispheres = np.array([i < n_regions // 2 for i in range(n_regions)])
    conn.configure()

    # Select neural mass model
    if model_name == "wilson_cowan":
        neural_model = lab.models.WilsonCowan()
    else:
        neural_model = lab.models.Generic2dOscillator(
            a=np.array([1.0]),
            b=np.array([-1.0]),
            c=np.array([0.0]),
            d=np.array([0.1]),
        )

    # Configure simulator
    sim = lab.simulator.Simulator(
        connectivity=conn,
        model=neural_model,
        coupling=lab.coupling.Linear(a=np.array([0.015])),
        integrator=lab.integrators.HeunStochastic(
            dt=0.5,
            noise=lab.noise.Additive(
                nsig=np.array([0.001]),
            ),
        ),
        monitors=[
            lab.monitors.TemporalAverage(period=1.0),  # 1ms sampling
        ],
        simulation_length=sim_length_ms,
    )
    sim.configure()

    # Run simulation — collect monitor outputs
    results = []
    times = []
    for output in sim():
        # output is a list of (time, data) tuples, one per monitor
        t_val, data = output[0]
        # data shape: (1, n_state_vars, n_regions, n_modes) or similar
        if data.ndim >= 3:
            results.append(data[0, :, 0] if data.shape[0] == 1 else data[:, 0, 0])
        elif data.ndim == 2:
            results.append(data[:, 0])
        else:
            results.append(np.atleast_1d(data))
        times.append(float(t_val) if np.isscalar(t_val) else float(t_val[0]))

    eeg_ts = np.array(results)  # (T, N) or similar
    # Ensure 2D: (T, N)
    if eeg_ts.ndim == 1:
        eeg_ts = eeg_ts.reshape(-1, 1)
    time_axis = np.array(times)

    return eeg_ts, time_axis
