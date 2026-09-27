"""Profile loading: type dispatch, validation, and the normalisation contract."""

import numpy as np
import pytest

from ieso import fcn as u
from ieso.errors import InputError


@pytest.fixture
def shape():
    return [1.0] * 10 + [3.0] * 10 + [2.0] * 4


def test_list_and_array_give_the_same_profile(horizon, shape):
    H = horizon(24)
    assert np.allclose(u.cf_h(shape, 0.5, hours=H), u.cf_h(np.array(shape), 0.5, hours=H))
    assert np.allclose(u.dm_h(shape, 100.0, hours=H), u.dm_h(np.array(shape), 100.0, hours=H))


def test_csv_matches_in_memory(horizon, shape, tmp_path):
    H = horizon(24)
    path = tmp_path / 'p.csv'
    path.write_text('\n'.join(str(v) for v in shape) + '\n')
    assert np.allclose(u.cf_h(str(path), 0.5, hours=H), u.cf_h(shape, 0.5, hours=H))
    assert np.allclose(u.dm_h(str(path), 100.0, hours=H), u.dm_h(shape, 100.0, hours=H))


def test_numpy_array_does_not_raise(horizon, shape):
    """Comparing an array with '' before checking its type raised ValueError."""
    H = horizon(24)
    u.cf_h(np.array(shape), 0.5, hours=H)
    u.dm_h(np.array(shape), 100.0, hours=H)


def test_empty_profile_is_flat(horizon):
    H = horizon(24)
    assert np.allclose(u.cf_h('', 0.4, hours=H), 0.4)
    assert np.allclose(u.dm_h('', 240.0, hours=H), 10.0)


def test_dm_h_preserves_the_total(horizon, shape):
    H = horizon(24)
    assert u.dm_h(shape, 137.0, hours=H) == pytest.approx([137.0 * v / sum(shape) for v in shape])
    assert sum(u.dm_h(shape, 137.0, hours=H)) == pytest.approx(137.0)


def test_cf_h_normalises_the_mean_to_the_target(horizon, shape):
    H = horizon(24)
    assert np.mean(u.cf_h(shape, 0.37, hours=H)) == pytest.approx(0.37)


def test_cf_h_can_exceed_one_and_that_is_the_documented_contract(horizon):
    """The profile supplies shape; capacity_factor sets the level.

    A profile whose own mean/max is below the requested capacity factor is
    scaled up until its mean matches, so its peak passes one. This is the
    behaviour the Swiss import series rely on, and it is why an explicit
    nameplate limit is needed rather than a bound that happens to clip.
    """
    H = horizon(24)
    shape = [1.0] * 12 + [0.5] * 12          # mean/max = 0.75
    assert max(u.cf_h(shape, 0.75, hours=H)) == pytest.approx(1.0)
    assert max(u.cf_h(shape, 0.80, hours=H)) == pytest.approx(0.80 / 0.75)
    assert max(u.cf_h(shape, 0.80, hours=H)) > 1.0


@pytest.mark.parametrize('bad, reason', [
    (np.ones((4, 6)), 'one-dimensional'),
    ([1.0] * 5, 'entries'),
    ([float('nan')] + [1.0] * 23, 'non-finite'),
    ([float('inf')] + [1.0] * 23, 'non-finite'),
    ([-1.0] + [1.0] * 23, 'negative'),
    ([0.0] * 24, 'sums to zero'),
    ('/no/such/file.csv', 'not found'),               # absolute, so no base is needed to look for it
    ('no/such/file.csv', 'cannot be resolved'),       # relative, and a bare call has no base
    (42, 'file path, a list or an array'),
])
def test_invalid_profiles_are_rejected(horizon, bad, reason):
    H = horizon(24)
    with pytest.raises(InputError) as info:
        u.cf_h(bad, 0.5, who='unit-under-test', hours=H)
    assert reason in str(info.value)
    assert info.value.entity == 'unit-under-test'


def test_rejection_names_the_entity(horizon):
    H = horizon(24)
    with pytest.raises(InputError) as info:
        u.cf_h([0.0] * 24, 0.5, who='solar-farm-7', hours=H)
    assert 'solar-farm-7' in str(info.value)
