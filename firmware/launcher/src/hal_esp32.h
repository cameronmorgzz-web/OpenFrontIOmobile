// ESP32-C3 SuperMini hardware layer for the launcher: samples switches/sensors
// into launcher::Inputs and drives motor (BTS7960), servos and the warning output
// from launcher::Outputs. No decisions are made here.
#pragma once

#include <cstdint>

#include "launcher_sm.h"

namespace hal {

void begin();
beer::launcher::Inputs readInputs();
void apply(const beer::launcher::Outputs& o);
uint32_t encoderEdges();

}  // namespace hal
