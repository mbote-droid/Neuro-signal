"""F-11, V-07 (H3): wPLI ignores volume conduction; PLV does not."""

from __future__ import annotations

import numpy as np

from neurosignal.features.connectivity import phase_coupling
from neurosignal.synth.eeg import coupled_pair, mixed_sources


def test_volume_conduction_inflates_plv_but_not_debiased_wpli():
    """V-07: no true coupling exists, only instantaneous mixing."""
    c = phase_coupling(mixed_sources(0, duration_s=300.0))
    plv, dwpli = c.upper("plv"), c.upper("dwpli")
    # negative control: the naive measure reports coupling that does not exist
    assert np.mean(plv > 0.3) >= 0.5
    assert np.percentile(dwpli, 95) <= 0.15


def test_debiased_wpli_is_unbiased_under_the_null():
    """Only the debiased estimator can go negative; its mean is near zero."""
    d = phase_coupling(mixed_sources(3, duration_s=120.0)).upper("dwpli")
    assert d.min() < 0
    assert abs(d.mean()) < 0.01


def test_lagged_coupling_is_found():
    """V-07: a truly lagged pair gives wPLI > 0.5."""
    c = phase_coupling(coupled_pair(0))
    assert c.wpli[0, 1] > 0.5
    assert c.dwpli[0, 1] > 0.5


def test_matrices_symmetric_with_nan_diagonal():
    """F-11."""
    c = phase_coupling(mixed_sources(1, duration_s=60.0))
    for m in (c.wpli, c.dwpli, c.plv):
        assert np.all(np.isnan(np.diag(m)))
        np.testing.assert_allclose(m, m.T, equal_nan=True)
    assert c.n_epochs == 30


def test_excluded_intervals_reduce_epochs():
    rec = mixed_sources(2, duration_s=60.0)
    assert phase_coupling(rec, exclude=[(10.0, 30.0)]).n_epochs == 20
