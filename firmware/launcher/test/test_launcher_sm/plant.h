// Simulated launcher mechanism ("plant") for hardware-in-the-loop style tests.
//
// Clay-pigeon-trap layout: a motor-driven cocking ring carries a two-stage latch
// that hooks the arm's catch roller. Units: positions in encoder edges along the
// ring travel, 0 = ring parked = arm home; `stroke` = cocked angle.
//   ring r: motor driven. The gearbox is backdrivable: with the arm latched the
//           spring load slows forward motion and drags the ring back when the
//           motor is not driving (coast fast, brake slow).
//   arm  a: follows the ring while latched. A latch TRIP (servo finger) releases
//           it: it flies home in ~80 ms and throws the can if one is in the cup.
//           The latch snaps onto the roller again when the ring returns to park.
// Motor model (linear speed/torque): v = v0 * pwm - v_load, where v0 is the
// no-load speed (ring return 0.67 s) and v_load the speed lost to the arm load
// (so that 100 % forward with the arm latched gives the cock time).
#pragma once

#include <cmath>
#include <cstdint>

#include "config.h"
#include "launcher_sm.h"

namespace sim {

using beer::launcher::Escapement;
using beer::launcher::Inputs;
using beer::launcher::Latch;
using beer::launcher::MotorDir;
using beer::launcher::Outputs;

struct PlantParams {
  double stroke = beer::cfg::kCockStrokeEdgesDefault;  // ring travel park -> cocked
  double cock_ms = 1290;          // 100 % forward, arm latched (4 m setting)
  double return_ms = 670;         // 100 % reverse, no load
  double fire_ms = 80;            // latch trip -> arm home
  uint32_t trip_release_ms = 60;  // servo finger travel until the latch lets go
  uint32_t can_drop_ms = 350;     // escapement release -> can in cup (+100 ms stable = 0.45 s feed)
  double coast_backdrive = 0.5;   // backdrive speed, fraction of v_load, motor coasting
  double brake_backdrive = 0.1;   // ... motor shorted (BTS7960 both HIGH)
  double end_stop_extra = 150;    // ring mechanical end stop beyond the cocked angle
  double switch_hyst = 20;        // SW_ARM_COCKED closes at stroke, opens below stroke - hyst
  double reverse_scale = 1.0;     // < 1: weak/slow reverse (fault injection)
};

class Plant {
 public:
  explicit Plant(const PlantParams& p = PlantParams()) : P(p) {}

  PlantParams P;

  // state
  double r = 0;  // ring
  double a = 0;  // arm
  bool latched = true;
  bool free_flight = false;
  bool cocked_sw = false;
  int mag = 10;
  bool can_in_cup = false;
  bool can_falling = false;
  uint32_t can_land_at = 0;
  Escapement last_esc = Escapement::Closed;
  Latch latch_cmd = Latch::Hold;
  uint32_t latch_cmd_since = 0;
  double enc_accum = 0;
  uint32_t t = 0;

  // observations
  int launched = 0;
  int misfed = 0;      // can dropped while the cup was not there
  int double_can = 0;  // second can dropped onto a full cup
  uint32_t motor_on_ms = 0;  // ticks with the motor driven

  // fault injection
  bool motor_jammed = false;         // rotor locked: nothing moves, no edges
  bool motor_dead = false;           // driving produces no torque (driven = coasting)
  bool cock_switch_dead = false;     // SW_ARM_COCKED never closes
  bool ring_home_switch_dead = false;
  bool arm_home_stuck_low = false;   // SW_ARM_HOME always closed
  bool arm_home_dead = false;        // SW_ARM_HOME never closes
  bool latch_jammed = false;         // TRIP does not release the arm
  bool esc_jammed = false;           // escapement drops nothing
  bool force_arm_cocked_low = false; // SW_ARM_COCKED stuck closed
  bool can_sensor_dead = false;      // SNS_CAN_IN_CUP stuck HIGH
  bool safety_pin_in = false;        // locks the ring and cuts latch-servo power
  bool test_button = false;

  double v0() const { return P.stroke / P.return_ms; }
  double vLoad() const { return v0() - P.stroke / P.cock_ms; }

  void setCocked() {  // arm latched at the cocked angle (e.g. power lost while armed)
    r = a = P.stroke;
    latched = true;
    cocked_sw = true;
  }

  Inputs inputs() const {
    Inputs in;
    in.arm_home = arm_home_stuck_low || (!arm_home_dead && a <= 5);
    in.arm_cocked = force_arm_cocked_low || (!cock_switch_dead && cocked_sw);
    in.ring_home = !ring_home_switch_dead && r <= 5;
    in.safety_pin_in = safety_pin_in;
    in.test_button = test_button;
    in.mag_empty = mag <= 0;
    in.can_in_cup = !can_sensor_dead && can_in_cup && a >= P.stroke - P.switch_hyst;
    in.enc_edges = static_cast<uint32_t>(enc_accum);
    return in;
  }

  void step(const Outputs& o) {
    ++t;
    // --- ring
    const bool driven = o.motor == MotorDir::Forward || o.motor == MotorDir::Reverse;
    if (driven) ++motor_on_ms;
    const double load = latched ? vLoad() : 0.0;
    const double p = o.pwm_pct / 100.0;
    double v = 0;
    MotorDir eff = o.motor;
    if (motor_dead && driven) eff = MotorDir::Coast;
    switch (eff) {
      case MotorDir::Forward: v = v0() * p - load; break;
      case MotorDir::Reverse: v = -v0() * p * P.reverse_scale - load; break;
      case MotorDir::Coast: v = -load * P.coast_backdrive; break;
      case MotorDir::Brake: v = -load * P.brake_backdrive; break;
    }
    if (motor_jammed || safety_pin_in) v = 0;
    double nr = r + v;
    if (nr < 0) nr = 0;
    if (nr > P.stroke + P.end_stop_extra) nr = P.stroke + P.end_stop_extra;
    // Position encoder: one edge per integer position crossed (either direction).
    enc_accum += std::fabs(std::floor(nr) - std::floor(r));
    r = nr;
    if (r >= P.stroke) cocked_sw = true;
    if (r < P.stroke - P.switch_hyst) cocked_sw = false;

    // --- latch servo finger
    if (o.latch != latch_cmd) {
      latch_cmd = o.latch;
      latch_cmd_since = t;
    }
    const bool tripped = latch_cmd == Latch::Trip && t - latch_cmd_since >= P.trip_release_ms;
    if (latched && tripped && !latch_jammed && !safety_pin_in && r > 5) {
      latched = false;
      free_flight = true;
    }

    // --- arm
    if (latched) {
      a = r;
    } else {
      if (a > 0) {
        a -= P.stroke / P.fire_ms;
        if (a <= 0) a = 0;
      }
      if (a <= 0 && r <= 5) latched = true;  // ring already parked when the arm lands
      if (a <= 0) {
        if (free_flight && can_in_cup) {
          ++launched;
          can_in_cup = false;
        }
        free_flight = false;
        if (r <= 5) latched = true;  // ring back at park: latch snaps onto the roller
      }
    }

    // --- escapement: one can per RELEASE edge (rocker)
    if (o.esc == Escapement::Release && last_esc == Escapement::Closed && !esc_jammed && mag > 0) {
      --mag;
      can_falling = true;
      can_land_at = t + P.can_drop_ms;
    }
    last_esc = o.esc;
    if (can_falling && t >= can_land_at) {
      can_falling = false;
      if (a >= P.stroke - P.switch_hyst) {
        if (can_in_cup) ++double_can;
        can_in_cup = true;
      } else {
        ++misfed;
      }
    }
  }

  bool armHome() const { return a <= 5; }
  bool ringHome() const { return r <= 5; }
};

}  // namespace sim
