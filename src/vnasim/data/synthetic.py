"""Synthetic S-parameter data generation.

Ported from VNAFrontEnd's SimulationDriver — generates a realistic
3-port duplexer response (low-band TX, high-band RX, TX-RX isolation).
"""

from __future__ import annotations

import numpy as np


def bandpass_response(
    freqs: np.ndarray,
    f_center: float,
    bandwidth: float,
    passband_loss_dB: float = -0.5,
    rejection_dB: float = -40.0,
    delay_ns: float = 2.0,
) -> np.ndarray:
    """Generate a bandpass-shaped complex S-parameter response.

    Uses a Gaussian magnitude envelope with linear phase (pure delay).
    """
    sigma = bandwidth / (2.0 * np.sqrt(2.0 * np.log(10)))
    mag_dB = rejection_dB + (passband_loss_dB - rejection_dB) * np.exp(
        -((freqs - f_center) / sigma) ** 2
    )
    mag = 10.0 ** (mag_dB / 20.0)
    phase = -2.0 * np.pi * freqs * delay_ns * 1e-9
    noise = np.random.default_rng(42).normal(0, 0.002, len(freqs))
    return mag * np.exp(1j * phase) + noise * (1 + 1j)


def isolation_response(
    freqs: np.ndarray,
    isolation_dB: float = -60.0,
    delay_ns: float = 1.0,
) -> np.ndarray:
    """Generate a flat high-isolation response with small noise."""
    mag = 10.0 ** (isolation_dB / 20.0)
    phase = -2.0 * np.pi * freqs * delay_ns * 1e-9
    noise = np.random.default_rng(99).normal(0, mag * 0.1, len(freqs))
    return mag * np.exp(1j * phase) + noise * (1 + 1j)


def reflection_from_transmission(s_tx: np.ndarray) -> np.ndarray:
    """Compute reflection assuming passivity: |S11|^2 ~ 1 - |S21|^2."""
    power = np.clip(1.0 - np.abs(s_tx) ** 2, 0.01, 1.0)
    mag = np.sqrt(power)
    phase = np.angle(s_tx) + np.pi / 3
    noise = np.random.default_rng(7).normal(0, 0.01, len(s_tx))
    return mag * np.exp(1j * phase) + noise * (1 + 1j)


# Default duplexer response parameters
_DUPLEXER_PARAMS = {
    "S21": dict(f_center=900e6, bandwidth=200e6,
                passband_loss_dB=-0.5, rejection_dB=-35.0, delay_ns=2.5),
    "S31": dict(f_center=1900e6, bandwidth=400e6,
                passband_loss_dB=-0.5, rejection_dB=-35.0, delay_ns=3.0),
    "S32": dict(f_center=1400e6, bandwidth=100e6,
                passband_loss_dB=-45.0, rejection_dB=-50.0, delay_ns=4.0),
}


def generate_param(
    param: str, freqs: np.ndarray, num_ports: int,
) -> np.ndarray:
    """Generate synthetic data for a single S-parameter."""
    p = param.upper()
    # Handle standard Sij format
    if len(p) >= 3 and p[0] == 'S' and p[1:].isdigit():
        i, j = int(p[1]), int(p[2])
    else:
        # Non-standard parameter — return isolation
        return isolation_response(freqs, isolation_dB=-60.0)

    if i > num_ports or j > num_ports:
        return isolation_response(freqs, isolation_dB=-80.0)

    # Reciprocity: S12=S21, S13=S31, S23=S32
    canonical = p
    if p not in _DUPLEXER_PARAMS:
        flipped = f"S{j}{i}"
        if flipped in _DUPLEXER_PARAMS:
            canonical = flipped

    if canonical in _DUPLEXER_PARAMS:
        return bandpass_response(freqs, **_DUPLEXER_PARAMS[canonical])

    # Diagonal (reflection)
    if i == j:
        if i == 1:
            s21 = bandpass_response(freqs, **_DUPLEXER_PARAMS["S21"])
            s31 = bandpass_response(freqs, **_DUPLEXER_PARAMS["S31"])
            power = np.clip(
                1.0 - np.abs(s21) ** 2 - np.abs(s31) ** 2, 0.01, 1.0,
            )
            mag = np.sqrt(power)
            phase = -2.0 * np.pi * freqs * 1.5e-9
            return mag * np.exp(1j * phase)
        elif i == 2:
            return reflection_from_transmission(
                bandpass_response(freqs, **_DUPLEXER_PARAMS["S21"])
            )
        elif i == 3:
            return reflection_from_transmission(
                bandpass_response(freqs, **_DUPLEXER_PARAMS["S31"])
            )
        else:
            return isolation_response(freqs, isolation_dB=-20.0)

    return isolation_response(freqs, isolation_dB=-60.0)
