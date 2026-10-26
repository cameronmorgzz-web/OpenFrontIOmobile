"""Gate 4 assembly checks: interference at rest/cocked/release, through the arm sweep and the
escapement stroke, and running clearances at the moving joints."""

import numpy as np
import pytest

from cad import checks as C
from cad import params as P
from cad.src import launcher as L

ARM_PARTS = {"hub_drum": L.hub_drum_local, "arm": L.arm_local, "hub_catch": L.hub_catch_local,
             "cup": L.cup_local, "cup_pad": L.cup_pad_local}
ESC = {"escapement_rocker", "esc_servo_mount", "hw_esc_servo", "hw_esc_rod"}


@pytest.fixture(scope="module")
def rest():
    return L.assembly("rest")


@pytest.mark.parametrize("state", ["rest", "cocked", "release"])
def test_no_interference(state):
    assert C.interference(state) == []


@pytest.mark.parametrize("state", ["rest", "cocked"])
def test_joint_clearances(state):
    for (a, b), d in C.joint_clearances(state).items():
        assert d >= P.CLR_SLIDE - 0.01, f"{a}/{b}: {d:.2f} mm in {state}"


def _hits(moving: dict, fixed: dict, skip=()):
    out = []
    for a, pa in moving.items():
        for b, pb in fixed.items():
            if b in moving or frozenset({a, b}) in C.INTENDED or b in skip:
                continue
            if C._bb_overlap(pa, pb) and (pa & pb).volume > C.TOL_VOL:
                out.append((a, b))
    return out


def test_arm_sweep_cocking_and_firing(rest):
    """Arm from rest to cocked (cup empty), then cocked -> release with a can in the cup.
    The ring and latch move with the arm (checked in the end states)."""
    fixed = {k: v for k, v in rest.items() if k not in L.MOVING_ARM and k not in L.MOVING_RING}
    bad = []
    for a in np.linspace(L.A_REST, L.A_COCKED, 12):
        parts = {n: L.place_arm(f(), a) for n, f in ARM_PARTS.items()}
        bad += [(round(a, 1),) + h for h in _hits(parts, fixed)]
    for a in np.linspace(L.A_COCKED, L.A_RELEASE, 10):
        parts = {n: L.place_arm(f(), a) for n, f in ARM_PARTS.items()}
        parts["can_in_cup"] = L.place_arm(L.can_solid((P.ARM_L, L.PZ)), a)
        bad += [(round(a, 1),) + h for h in _hits(parts, fixed, skip={"can_mag_1"} if a < L.A_COCKED else ())]
    assert bad == []


def test_escapement_stroke(rest):
    """Rocker, horn and pushrod through the whole servo stroke. Past the stage angle can1 has
    already rolled away (sim/feed_sim.py), so it is not an obstacle there."""
    fixed = {k: v for k, v in rest.items() if k not in ESC}
    fixed["esc_servo_mount"] = rest["esc_servo_mount"]
    bad = []
    for phi in np.linspace(L.ESC_PHI_HOLD, L.ESC_PHI_REL, 9):
        pose = L.escapement_pose(phi)
        skip = {"can_mag_1"} if phi > L.ESC_PHI_STAGE else set()
        bad += [(round(phi),) + h for h in _hits(pose, fixed, skip)]
        assert not _hits({"escapement_rocker": pose["escapement_rocker"]}, {"hw_esc_servo": pose["hw_esc_servo"]})
    assert bad == []


def test_escapement_kinematics():
    # stage: f1 still blocks can1 (top above the can centre minus 5 mm), release: f1 below the rail
    import math
    ax = L.rocker_axle()
    up = (0.5, 0.866)

    def top(s0, h, th):
        q = L.chute_s(s0)
        t = (q[0] + h * up[0], q[1] + h * up[1])
        c, s = math.cos(th), math.sin(th)
        x, z = t[0] - ax[0], t[1] - ax[1]
        p = (ax[0] + x * c - z * s, ax[1] + x * s + z * c)
        return (p[0] - q[0]) * up[0] + (p[1] - q[1]) * up[1] + 3.5
    assert top(L.ROCKER_S1, L.ROCKER_F1_H, L.esc_theta(L.ESC_PHI_STAGE)) > 25.0
    assert top(L.ROCKER_S1, L.ROCKER_F1_H, L.esc_theta(L.ESC_PHI_REL)) < 0.0
    assert top(L.ROCKER_S2, L.ROCKER_F2_H, 0.0) <= -0.9          # f2 below the rail at hold
    assert top(L.ROCKER_S2, L.ROCKER_F2_H, L.esc_theta(L.ESC_PHI_REL)) > 18.0
