"""Every exploit works on the paper's harness and none works on esoforge's."""
from esoforge.probes import HARDENED_PROBES, PROBES, run_hardened_probes, run_official_probes


def test_official_harness_is_exploitable_by_every_probe():
    results = run_official_probes()
    assert {r.name for r in results} == set(PROBES)
    assert all(r.exploited for r in results), [r.name for r in results if not r.exploited]


def test_hardened_harness_blocks_every_probe():
    results = run_hardened_probes()
    assert {r.name for r in results} == set(HARDENED_PROBES)
    assert not any(r.exploited for r in results), [r.name for r in results if r.exploited]
