"""A video of one shot: the physics is the MuJoCo launch model (sim/launch.py, the same model the
Monte Carlo study runs), dressed in the CAD meshes. Real-time pass, then a 20x slow-motion replay.

    python -m sim.video                  -> sim/video/launch_4m.mp4

The moving can, the arm (with hub and cup) and the gate are the simulated bodies. The ring and pinion
follow the arm while the latch holds them together, then stay put. Magazine cans are drawn static.
"""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "osmesa")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from cad import checks as C  # noqa: E402
from cad import params as P  # noqa: E402
from cad.src import launcher as L  # noqa: E402
from sim.launch import H_CATCH, run  # noqa: E402
from sim.model import MM, Variation, build_xml  # noqa: E402

OUT = Path(__file__).resolve().parent / "video"
W, H, FPS = 1280, 720, 30
DT = 0.0002                       # sim/model.py timestep
PRELOAD_MM, DETENT = 55.0, 4.0    # the calibrated 4 m setting (sim/mc_results.json nominal, CALIBRATION.md)
INTRO = 0.8                       # s of still frame at the button press (the motor starts with the beacon)
SLOW = 20
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PSI_OFF = L.PSI_COCKED - L.A_COCKED          # ring angle - arm angle while the latch holds them


def _quat_about_neg_y(deg):
    a = math.radians(deg) / 2
    return np.array([math.cos(a), 0.0, -math.sin(a), 0.0])


def _stl(part, tmp: Path, name: str, shift=(0.0, 0.0, 0.0)) -> str:
    mesh = C.to_mesh(part, tol=0.25, ang=0.3)
    mesh.apply_translation(shift)
    mesh.apply_scale(0.001)
    f = tmp / f"{name}.stl"
    mesh.export(f)
    return str(f)


def _rgba(name):
    from cad.build import SPECS
    if name in SPECS:
        r, g, b = SPECS[name].color
    elif name.startswith("can"):
        r, g, b = 0.75, 0.12, 0.12
    elif name.startswith("hw_"):
        r, g, b = 0.45, 0.46, 0.48
    else:
        r, g, b = 0.6, 0.6, 0.6
    return f"{r} {g} {b} 1"


def scene_xml(var: Variation, x_rel: float, x_land: float) -> str:
    """The physics model's XML plus visual-only CAD geometry (contype/conaffinity 0)."""
    xml = build_xml(var, can_start="chute")
    # hide the simulation's collision boxes (the CAD meshes are drawn instead); keep the can
    xml = re.sub(r'(<geom name="(cup_\w+|beam|rail[+-]1|wall[+-]1)"[^>]*?)rgba="[^"]*"', r'\1rgba="0 0 0 0"', xml)
    xml = xml.replace('rgba=".2 .2 .2 1"/></body>', 'rgba="0 0 0 0"/></body>')          # the sim gate
    tmp = Path(tempfile.mkdtemp())
    assets, world, armg = [], [], []
    vis = 'contype="0" conaffinity="0"'

    def mesh(name, part, shift=(0.0, 0.0, 0.0)):
        assets.append(f'<mesh name="{name}" file="{_stl(part, tmp, name, shift)}"/>')

    asm = L.assembly("rest")
    skip = L.MOVING_ARM | L.MOVING_RING | {"hw_pinion", "escapement_rocker", "hw_esc_rod", "hw_esc_servo",
                                           "can_mag_1", "can_in_cup", "hw_springs"}
    for n, p in asm.items():
        if n in skip:
            continue
        mesh(n, p)
        world.append(f'<geom name="v_{n}" type="mesh" mesh="{n}" rgba="{_rgba(n)}" {vis}/>')
    # escapement: hold and released poses, switched by alpha per frame
    for tag, phi in (("hold", L.ESC_PHI_HOLD), ("rel", L.ESC_PHI_REL)):
        for n, p in L.escapement_pose(phi).items():
            mesh(f"{n}_{tag}", p)
            world.append(f'<geom name="v_{n}_{tag}" type="mesh" mesh="{n}_{tag}" rgba="{_rgba(n)}" {vis}/>')
    # arm-borne parts in the arm body frame (pivot at the origin, alpha = 0)
    pin, roller = L.catch_pin_local()
    for n, p in (("arm", L.arm_local()), ("hub_drum", L.hub_drum_local()), ("hub_catch", L.hub_catch_local()),
                 ("cup", L.cup_local()), ("cup_pad", L.cup_pad_local()), ("hw_catch_pin", pin), ("hw_catch_roller", roller)):
        mesh(f"a_{n}", p, (0.0, 0.0, -L.PZ))
        armg.append(f'<geom type="mesh" mesh="a_{n}" rgba="{_rgba(n)}" {vis}/>')
    # ring (+ latch, nose dowel) and pinion as mocap bodies
    ring = [("ring_gear", L.ring_gear_local()), ("ring_latch", L.ring_latch_local(0.0)), ("hw_nose_dowel", L.nose_dowel_local())]
    for n, p in ring:
        mesh(f"r_{n}", p, (0.0, 0.0, -L.PZ))
    mx, mz = L.abs_xz(L.MOTOR_C)
    mesh("p_pinion", L.pinion_solid(0.0), (-mx, 0.0, -mz))
    ringb = "".join(f'<geom type="mesh" mesh="r_{n}" rgba="{_rgba(n)}" {vis}/>' for n, _ in ring)
    # floor marks every metre from the release point, and the catch point
    marks = "".join(
        f'<geom type="box" pos="{x_rel + k} 0 0.0005" size="0.006 0.35 0.0005" rgba=".35 .38 .4 1" {vis}/>'
        for k in range(1, 6))
    marks += (f'<geom type="box" pos="{x_rel + 2.5} 0 0.0004" size="2.5 0.002 0.0004" rgba=".35 .38 .4 1" {vis}/>'
              f'<geom type="cylinder" pos="{x_land} 0 {H_CATCH}" size="0.11 0.004" euler="90 0 0" rgba=".15 .65 .35 .45" {vis}/>'
              f'<geom type="cylinder" pos="{x_land} 0 {H_CATCH / 2}" size="0.006 {H_CATCH / 2}" rgba=".15 .65 .35 .6" {vis}/>')
    pz = L.PZ * MM
    extra_world = f"""
    <light directional="true" pos="-1 -2 3" dir="0.3 0.6 -1" diffuse="0.6 0.6 0.6" castshadow="true"/>
    <light directional="true" pos="2 2 2" dir="-0.5 -0.3 -1" diffuse="0.25 0.25 0.25" castshadow="false"/>
    {''.join(world)}{marks}
    <body name="ring" mocap="true" pos="0 0 {pz}">{ringb}</body>
    <body name="pinion" mocap="true" pos="{mx * MM} 0 {mz * MM}"><geom type="mesh" mesh="p_pinion" rgba="{_rgba('hw_pinion')}" {vis}/></body>"""
    xml = xml.replace('<geom name="floor" type="plane" size="20 20 .1" contype="0" conaffinity="0" rgba=".9 .9 .9 1"/>',
                      '<geom name="floor" type="plane" size="20 20 .1" contype="0" conaffinity="0" material="floor"/>')
    xml = xml.replace("<worldbody>", "<worldbody>" + extra_world, 1)
    xml = xml.replace('<joint name="pivot"', "".join(armg) + '\n      <joint name="pivot"', 1)
    head = f"""<visual><global offwidth="{W}" offheight="{H}" fovy="40"/><quality shadowsize="8192" offsamples="8"/>
    <headlight ambient="0.38 0.38 0.38" diffuse="0.4 0.4 0.4" specular="0.05 0.05 0.05"/><map znear="0.005"/></visual>
    <asset>{''.join(assets)}<texture type="skybox" builtin="gradient" rgb1="1 1 1" rgb2=".84 .87 .9" width="512" height="512"/>
    <texture name="grid" type="2d" builtin="checker" rgb1=".93 .94 .95" rgb2=".89 .9 .92" width="512" height="512"/>
    <material name="floor" texture="grid" texrepeat="20 20" reflectance="0"/></asset>"""
    return xml.replace("<worldbody>", head + "<worldbody>", 1)


class Cam:
    def __init__(self, lookat, dist, az, el):
        self.lookat, self.dist, self.az, self.el = np.array(lookat, float), dist, az, el

    def lerp(self, o: "Cam", u: float) -> "Cam":
        u = 0.5 - 0.5 * math.cos(math.pi * min(max(u, 0.0), 1.0))
        return Cam(self.lookat + (o.lookat - self.lookat) * u, self.dist + (o.dist - self.dist) * u,
                   self.az + (o.az - self.az) * u, self.el + (o.el - self.el) * u)

    def mj(self):
        c = mujoco.MjvCamera()
        c.lookat[:] = self.lookat
        c.distance, c.azimuth, c.elevation = self.dist, self.az, self.el
        return c

    def project(self, p, fovy=40.0):
        """World point -> pixel (MuJoCo free-camera convention)."""
        az, el = math.radians(self.az), math.radians(self.el)
        fwd = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        pos = self.lookat - self.dist * fwd
        right = np.cross(fwd, [0, 0, 1.0])
        right /= np.linalg.norm(right)
        up = np.cross(right, fwd)
        v = np.array(p) - pos
        z = v @ fwd
        if z <= 0.01:
            return None
        f = (H / 2) / math.tan(math.radians(fovy) / 2)
        return (W / 2 + f * (v @ right) / z, H / 2 - f * (v @ up) / z)


CLOSE = Cam([-0.12, 0.0, 0.30], 1.05, 118, -14)
WIDE = Cam([2.05, 0.0, 0.85], 5.6, 90, -4)
SLOWCAM = Cam([0.02, 0.0, 0.40], 0.95, 100, -6)


def main():
    OUT.mkdir(exist_ok=True)
    var = replace(Variation(), preload_mm=PRELOAD_MM)
    trace: list = []
    res = run(var, release_deg=DETENT, do_cock=True, trace=trace, flight_to_floor=True)
    assert res.ok, res.reason
    x_land = res.x_release + res.range_m
    m = mujoco.MjModel.from_xml_string(scene_xml(var, res.x_release, x_land))
    d = mujoco.MjData(m)
    r = mujoco.Renderer(m, H, W)
    can_id = mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "can")
    ring_mid = m.body_mocapid[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "ring")]
    pin_mid = m.body_mocapid[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "pinion")]
    gate_mid = m.body_mocapid[mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_BODY, "gate")]
    near = [i for i in range(m.ngeom) if (mujoco.mj_id2name(m, mujoco.mjtObj.mjOBJ_GEOM, i) or "").startswith(
        tuple(f"v_{n}" for n in ("side_plate_left", "side_cheek_left", "mag_wall_left", "mag_chute_left", "base_",
                                  "esc_servo_mount", "stop_bracket", "hw_absorber", "shaft_cap_left", "shaft_spacer_left")))]
    esc = {tag: [mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_GEOM, f"v_{n}_{tag}") for n in
                 ("escapement_rocker", "hw_esc_rod", "hw_esc_servo")] for tag in ("hold", "rel")}
    phases = [p for p, _, _ in trace]
    i_feed = phases.index("feed")
    i_fire = phases.index("fire")
    i_flight = phases.index("flight")
    zc = m.jnt_qposadr[m.body_jntadr[can_id]] + 2
    i_catch = next(i for i in range(i_flight + 1, len(trace))       # coming DOWN through the catch height
                   if trace[i][1][zc] <= H_CATCH < trace[i - 1][1][zc] and trace[i][1][zc] < trace[i - 1][1][zc])
    q0 = trace[0][1]
    a0 = math.degrees(q0[0])
    psi_fire = math.degrees(trace[i_fire][1][0]) + PSI_OFF

    font = ImageFont.truetype(FONT, 26)
    font_s = ImageFont.truetype(FONT, 20)
    font_b = ImageFont.truetype(FONT_B, 34)

    def pose(i):
        _, q, mp = trace[i]
        d.qpos[:] = q
        d.mocap_pos[gate_mid] = mp[0]
        alpha = math.degrees(q[0])
        psi = alpha + PSI_OFF if i < i_fire else psi_fire
        d.mocap_quat[ring_mid] = _quat_about_neg_y(psi)
        d.mocap_quat[pin_mid] = _quat_about_neg_y(-(psi - (a0 + PSI_OFF)) * P.RING_TEETH / P.PINION_TEETH)
        released = i_feed <= i < i_feed + int(0.30 / DT)
        for tag, ids in esc.items():
            on = (tag == "rel") == released
            for g in ids:
                m.geom_rgba[g][3] = 1.0 if on else 0.0
        mujoco.mj_forward(m, d)

    def speed(i):
        if i == 0:
            return 0.0
        a = m.jnt_qposadr[m.body_jntadr[can_id]]
        return float(np.linalg.norm(trace[i][1][a:a + 3] - trace[i - 1][1][a:a + 3]) / DT)

    def frame(i, cam: Cam, labels: list[str], mode: str, warn: bool):
        pose(i)
        cut = cam.dist < 1.5                     # close-ups: near-side frame parts see-through
        for g in near:
            m.geom_rgba[g][3] = 0.18 if cut else 1.0
        r.update_scene(d, camera=cam.mj())
        img = Image.fromarray(r.render())
        dr = ImageDraw.Draw(img, "RGBA")
        dr.rounded_rectangle((20, 20, 560, 60 + 36 * len(labels)), 12, fill=(255, 255, 255, 215))
        dr.text((38, 30), labels[0], font=font_b, fill=(20, 26, 24))
        for k, t in enumerate(labels[1:]):
            dr.text((38, 78 + 34 * k), t, font=font, fill=(50, 58, 55))
        dr.rounded_rectangle((W - 300, 20, W - 20, 64), 12, fill=(255, 255, 255, 215))
        dr.text((W - 284, 29), mode, font=font, fill=(160, 70, 10) if "slow" in mode else (40, 110, 60))
        if warn:
            dr.ellipse((W - 74, 80, W - 30, 124), fill=(235, 120, 20, 230))
            dr.text((W - 205, 88), "WARNING", font=font_s, fill=(200, 90, 10))
        if cam is not CLOSE and cam.dist > 3:
            for k in range(1, 6):
                px = cam.project((res.x_release + k, -0.35, 0.0))
                if px:
                    dr.text((px[0] - 16, px[1] + 6), f"{k} m", font=font_s, fill=(60, 66, 70))
            pc = cam.project((x_land, 0.0, H_CATCH + 0.12))
            if pc:
                dr.text((pc[0] - 52, pc[1] - 30), "catch 0.9 m", font=font_s, fill=(25, 120, 60))
        dr.text((22, H - 34), "Physics: MuJoCo launch model (same as the Monte Carlo) · geometry: the kit's CAD"
                + (" · near side plate see-through" if cut else ""), font=font_s, fill=(70, 76, 80))
        return np.asarray(img.convert("RGB"))

    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
                           "-movflags", "+faststart", str(OUT / "launch_4m.mp4")], stdin=subprocess.PIPE)

    def emit(img):
        ff.stdin.write(img.tobytes())

    t_fire = i_fire * DT
    phase_name = {"cock": "COCK: motor pulls the arm back", "hold": "COCKED: latch holds", "feed": "FEED: one can rolls in",
                  "armed": "ARMED", "fire": "FIRE: latch trips", "flight": "FLIGHT"}
    # 1) WARN intro (button pressed; in the real machine the motor starts with the beacon)
    for k in range(int(INTRO * FPS)):
        emit(frame(0, CLOSE, ["Button pressed", "beacon + buzzer on", "t = 0.00 s"], "real time", warn=(k // 8) % 2 == 0))
    # 2) real time
    n = i_catch + 1                              # real time ends at the catch
    for f in range(int(n * DT * FPS) + 1):
        i = min(int(f / FPS / DT), n - 1)
        t = i * DT
        if t < t_fire:
            cam = CLOSE
        else:   # follow the can at a medium distance
            cx = float(np.clip(trace[i][1][zc - 2], 0.3, x_land))
            follow = Cam([cx * 0.85 + 0.15, 0.0, 0.95], 2.9, 92, -5)
            cam = CLOSE.lerp(follow, (t - t_fire) / 0.35)
        lab = [phase_name[phases[i]], f"t = {t:.2f} s since the button", f"can speed {speed(i):.1f} m/s"]
        if i >= i_catch:
            lab = ["CAUGHT at 0.9 m", f"range {res.range_m:.2f} m · catch {res.v_catch:.1f} m/s", f"peak {res.peak_z:.2f} m"]
        emit(frame(i, cam, lab, "real time", warn=True))
    last = Cam([float(np.clip(trace[n - 1][1][zc - 2], 0.3, x_land)) * 0.85 + 0.15, 0.0, 0.95], 2.9, 92, -5)
    for k in range(int(1.5 * FPS)):
        emit(frame(n - 1, last.lerp(WIDE, k / (1.2 * FPS)), ["CAUGHT at 0.9 m", f"range {res.range_m:.2f} m · catch {res.v_catch:.1f} m/s",
                                 f"peak {res.peak_z:.2f} m"], "real time", warn=False))
    # 3) slow-motion replay of the swing and release
    i0, i1 = i_fire - int(0.02 / DT), min(i_fire + int(0.22 / DT), n - 1)
    step = max(1, int(1 / (FPS * SLOW) / DT))
    for i in range(i0, min(i1, n - 1), step):
        alpha = math.degrees(trace[i][1][0])
        lab = [phase_name[phases[i]] if phases[i] != "flight" else "RELEASE: can leaves the cup",
               f"t = {(i - i_fire) * DT * 1000:+.0f} ms from trip · arm at {alpha:.0f}°",
               f"can speed {speed(i):.1f} m/s"]
        emit(frame(i, SLOWCAM, lab, f"slow motion {SLOW}x", warn=False))
    # 4) end card
    end = [f"Range {res.range_m:.2f} m at the 4 m setting", f"launch {res.v_release:.2f} m/s at {res.angle_release:.1f}°",
           f"catch {res.v_catch:.2f} m/s · peak {res.peak_z:.2f} m", "Simulation, not reality: calibrate."]
    for _ in range(int(2.5 * FPS)):
        emit(frame(n - 1, WIDE, end, "summary", warn=False))
    ff.stdin.close()
    ff.wait()
    r.close()
    print(OUT / "launch_4m.mp4", res.range_m, res.v_release, res.angle_release, res.v_catch, res.peak_z)


if __name__ == "__main__":
    main()
