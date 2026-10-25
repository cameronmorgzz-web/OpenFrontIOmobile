"""Product renders with MuJoCo's offscreen renderer (OSMesa/EGL), from the real CAD meshes.

    MUJOCO_GL=osmesa python -m cad.render
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("MUJOCO_GL", "osmesa")

import mujoco  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from cad import checks as C  # noqa: E402
from cad.src import button as BTN  # noqa: E402
from cad.src import launcher as L  # noqa: E402

OUT = Path(__file__).resolve().parent / "renders"
W, H = 1600, 1200

HW_COLORS = {
    "hw_springs": (0.75, 0.76, 0.78), "hw_shaft": (0.7, 0.7, 0.72), "hw_absorber": (0.2, 0.2, 0.22),
    "hw_motor": (0.55, 0.56, 0.58), "hw_pinion": (0.6, 0.6, 0.62), "hw_latch_servo": (0.1, 0.1, 0.12),
    "hw_catch_pin": (0.7, 0.7, 0.72), "hw_catch_roller": (0.7, 0.7, 0.72), "hw_nose_dowel": (0.7, 0.7, 0.72),
    "hw_safety_pin": (0.75, 0.75, 0.78), "hw_switch": (0.7, 0.7, 0.72), "hw_lipo": (0.2, 0.3, 0.6),
    "hw_esp32": (0.1, 0.35, 0.15), "hw_tp4056": (0.1, 0.2, 0.5),
}
CAN_COLOR = (0.75, 0.12, 0.12)


def _color(name):
    from cad.build import SPECS
    if name in SPECS:
        return SPECS[name].color
    if name.startswith("can"):
        return CAN_COLOR
    return HW_COLORS.get(name, (0.6, 0.6, 0.6))


def _scene(parts: dict, offsets: dict | None = None, floor=True) -> mujoco.MjModel:
    tmp = Path(tempfile.mkdtemp())
    assets, geoms = [], []
    for name, part in parts.items():
        mesh = C.to_mesh(part, tol=0.15, ang=0.25)
        if offsets and name in offsets:
            mesh.apply_translation(offsets[name])
        mesh.apply_scale(0.001)
        f = tmp / f"{name}.stl"
        mesh.export(f)
        r, g, b = _color(name)
        spec = 0.6 if name.startswith(("hw_", "can")) else 0.25
        assets.append(f'<mesh name="{name}" file="{f}"/>'
                      f'<material name="m_{name}" rgba="{r} {g} {b} 1" specular="{spec}" shininess="0.6" reflectance="0.0"/>')
        geoms.append(f'<geom type="mesh" mesh="{name}" material="m_{name}"/>')
    fl = ('<geom type="plane" size="3 3 0.01" pos="0 0 -0.0005" material="floor"/>' if floor else "")
    xml = f"""<mujoco><visual><global offwidth="{W}" offheight="{H}"/><quality shadowsize="8192"/>
    <headlight ambient="0.35 0.35 0.35" diffuse="0.45 0.45 0.45" specular="0.1 0.1 0.1"/></visual>
    <asset>{''.join(assets)}<texture type="skybox" builtin="gradient" rgb1="1 1 1" rgb2=".86 .88 .9" width="512" height="512"/>
      <material name="floor" rgba=".95 .95 .96 1" reflectance="0"/></asset>
    <worldbody><light directional="true" pos="-1 -1 2" dir="0.4 0.6 -1" diffuse="0.55 0.55 0.55" castshadow="true"/>
    <light directional="true" pos="1 1 2" dir="-0.5 -0.3 -1" diffuse="0.25 0.25 0.25" castshadow="false"/>
    {fl}{''.join(geoms)}</worldbody></mujoco>"""
    return mujoco.MjModel.from_xml_string(xml)


def _shot(model, lookat, dist, az, el, path):
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    r = mujoco.Renderer(model, H, W)
    cam = mujoco.MjvCamera()
    cam.lookat[:] = lookat
    cam.distance, cam.azimuth, cam.elevation = dist, az, el
    r.update_scene(data, camera=cam)
    img = r.render()
    Image.fromarray(img).save(path)
    r.close()


def render_all():
    OUT.mkdir(exist_ok=True)
    asm = L.assembly("rest")
    m = _scene(asm)
    look = [-0.12, 0.0, 0.2]
    _shot(m, look, 1.25, 150, -18, OUT / "launcher_front_left.png")
    _shot(m, look, 1.25, 35, -22, OUT / "launcher_rear_right.png")
    _shot(m, look, 1.15, 90, -3, OUT / "launcher_side.png")
    _shot(m, [-0.12, 0, 0.25], 1.35, 120, -45, OUT / "launcher_top.png")
    cocked = L.assembly("cocked")
    _shot(_scene(cocked), look, 1.15, 90, -3, OUT / "launcher_side_cocked.png")
    # exploded view: groups pushed apart along y / z
    off = {}
    for n in asm:
        y = 0.0
        if n in ("side_plate_right", "motor_cover", "hw_motor", "side_cheek_right", "shaft_cap_right", "safety_pin_handle",
                 "hw_safety_pin"):
            y = 170.0
        elif n in ("ring_gear", "ring_latch", "hw_nose_dowel", "hw_pinion", "gear_guard", "latch_servo_mount",
                   "hw_latch_servo", "shaft_spacer_mid"):
            y = 95.0
        elif n in ("side_plate_left", "side_cheek_left", "shaft_cap_left", "stop_bracket", "hw_absorber",
                   "shaft_spacer_left"):
            y = -160.0
        z = 0.0
        if n.startswith("mag_wall") and "upper" in n or n == "mag_bridge_top":
            z = 120.0
        if n.startswith("can_mag"):
            z = 260.0
        if n in ("ebox_lid",):
            z = 160.0
        if n in ("cup", "cup_pad", "can_in_cup"):
            z = 80.0
        if n.startswith("base") or n.startswith("spring") or n == "hw_springs":
            z = -90.0
        off[n] = (0.0, y, z)
    _shot(_scene(asm, off, floor=False), [-0.12, 0, 0.2], 1.75, 135, -20, OUT / "launcher_exploded.png")
    # button
    b = BTN.assembly(0.0)
    bm = _scene(b)
    _shot(bm, [0, 0, 0.026], 0.22, 135, -30, OUT / "button.png")
    boff = {"btn_cap": (0, 0, 60), "btn_switch_plate": (0, 0, 35), "hw_switch": (0, 0, 35), "btn_tray": (0, 0, 18),
            "hw_esp32": (0, 0, 18), "hw_tp4056": (0, 0, 18), "hw_lipo": (0, 0, 8),
            "btn_foot_ring": (0, 0, -45), "btn_shell": (0, 0, 0)}
    _shot(_scene(b, boff, floor=False), [0, 0, 0.03], 0.34, 135, -15, OUT / "button_exploded.png")


if __name__ == "__main__":
    render_all()
