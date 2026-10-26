// Beer Button firmware (ESP32-C3 SuperMini).
//
// Life cycle: deep sleep -> press wakes the chip (GPIO3 LOW) -> read battery ->
// WiFi STA + ESP-NOW on channel 1 (no scan) -> FIRE (seq+1, persisted first) ->
// up to 3 retries with the same seq, 120 ms ACK wait each -> haptic/LED feedback ->
// optional long press (>= 5 s) -> pairing -> wait for release -> deep sleep.
//
// All decisions (battery hysteresis, retry policy, press timing, ACK checks) live
// in ../common and are unit tested; this file is only the hardware glue.

#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <driver/gpio.h>
#include <esp_arduino_version.h>
#include <esp_now.h>
#include <esp_sleep.h>
#include <esp_system.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>

#include <cstring>

#include "button_logic.h"
#include "config.h"
#include "protocol.h"

using namespace beer;

namespace {

// ------------------------------------------------------------------- pins --
constexpr uint8_t kPinSwitch = 3;  // big switch to GND, external 1 MOhm pull-up, wake source
constexpr uint8_t kPinBatt = 1;    // battery through 1M/1M divider (x2)
constexpr uint8_t kPinHaptic = 4;  // coin motor via NPN, active high
constexpr uint8_t kPinLed = 5;     // status LED, active high (330 Ohm)

constexpr uint32_t kRtcMagic = 0xBEE5B077u;
constexpr const char* kNvsNs = "beerbtn";

// State that survives deep sleep (lost on battery removal / reset).
struct RtcState {
  uint32_t magic;
  uint32_t seq;  // last sequence number SENT
  bool low_batt;
  bool paired;
  uint8_t key[proto::kKeyLen];
  uint8_t launcher_mac[proto::kMacLen];
};
RTC_DATA_ATTR RtcState g_rtc;

struct RxFrame {
  uint8_t mac[proto::kMacLen];
  uint8_t len;
  uint8_t data[proto::kPacketLen];
};
QueueHandle_t g_rxq = nullptr;
Preferences g_prefs;
const uint8_t kBroadcast[proto::kMacLen] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

bool switchPressed() { return digitalRead(kPinSwitch) == LOW; }

void led(bool on) { digitalWrite(kPinLed, on ? HIGH : LOW); }
void haptic(bool on) { digitalWrite(kPinHaptic, on ? HIGH : LOW); }

void blink(uint8_t n, uint32_t on_ms, uint32_t off_ms) {
  for (uint8_t i = 0; i < n; ++i) {
    led(true);
    delay(on_ms);
    led(false);
    delay(off_ms);
  }
}

// ------------------------------------------------------------ persistence --
void loadState(bool warm) {
  g_prefs.begin(kNvsNs, false);
  const uint32_t nvs_seq = g_prefs.getUInt("seq", 0);
  if (warm && g_rtc.magic == kRtcMagic) {
    g_rtc.seq = btn::bootSequence(true, g_rtc.seq, nvs_seq);
    return;
  }
  // Cold boot: NVS is the source of truth, plus a safety jump in case the last
  // write did not land before power was lost.
  std::memset(&g_rtc, 0, sizeof(g_rtc));
  g_rtc.magic = kRtcMagic;
  g_rtc.seq = btn::bootSequence(false, 0, nvs_seq);
  g_rtc.paired = g_prefs.getBool("paired", false);
  if (g_rtc.paired) {
    const size_t k = g_prefs.getBytes("key", g_rtc.key, sizeof(g_rtc.key));
    const size_t m = g_prefs.getBytes("lmac", g_rtc.launcher_mac, sizeof(g_rtc.launcher_mac));
    g_rtc.paired = (k == sizeof(g_rtc.key) && m == sizeof(g_rtc.launcher_mac));
  }
  g_prefs.putUInt("seq", g_rtc.seq);
}

// Reserve the next sequence number: persisted BEFORE it goes on air.
uint32_t nextSeq() {
  g_rtc.seq += 1;
  g_prefs.putUInt("seq", g_rtc.seq);
  return g_rtc.seq;
}

// ---------------------------------------------------------------- battery --
uint16_t readBatteryMv() {
  uint32_t sum = 0;
  for (uint8_t i = 0; i < cfg::kBtnBattSamples; ++i) sum += analogReadMilliVolts(kPinBatt);
  return btn::batteryMvFromAdc(sum, cfg::kBtnBattSamples);
}

// ------------------------------------------------------------------ radio --
#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  const uint8_t* mac = info->src_addr;
#else
void onRecv(const uint8_t* mac, const uint8_t* data, int len) {
#endif
  if (g_rxq == nullptr || len != static_cast<int>(proto::kPacketLen)) return;
  RxFrame f;
  std::memcpy(f.mac, mac, sizeof(f.mac));
  f.len = static_cast<uint8_t>(len);
  std::memcpy(f.data, data, proto::kPacketLen);
  xQueueSend(g_rxq, &f, 0);
}

bool addPeer(const uint8_t mac[proto::kMacLen]) {
  if (esp_now_is_peer_exist(mac)) return true;
  esp_now_peer_info_t peer;
  std::memset(&peer, 0, sizeof(peer));
  std::memcpy(peer.peer_addr, mac, proto::kMacLen);
  peer.channel = cfg::kEspNowChannel;
  peer.ifidx = WIFI_IF_STA;
  peer.encrypt = false;
  return esp_now_add_peer(&peer) == ESP_OK;
}

bool radioInit() {
  g_rxq = xQueueCreate(8, sizeof(RxFrame));
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(cfg::kEspNowChannel, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) return false;
  esp_now_register_recv_cb(onRecv);
  return true;
}

// FIRE with retries. Returns true on a valid signed ACK for this seq.
bool sendFire(uint16_t batt_mv) {
  if (!addPeer(g_rtc.launcher_mac)) return false;
  const uint32_t seq = nextSeq();
  uint8_t pkt[proto::kPacketLen];
  proto::pack(proto::makeFire(seq, batt_mv, g_rtc.low_batt), g_rtc.key, pkt);

  btn::RetryPolicy policy;
  policy.start(millis());
  bool acked = false;
  for (;;) {
    switch (policy.poll(millis(), acked)) {
      case btn::RetryPolicy::Action::Send:
        esp_now_send(g_rtc.launcher_mac, pkt, sizeof(pkt));
        break;
      case btn::RetryPolicy::Action::Acked:
        return true;
      case btn::RetryPolicy::Action::GiveUp:
        return false;
      case btn::RetryPolicy::Action::Wait:
        break;
    }
    RxFrame f;
    if (xQueueReceive(g_rxq, &f, pdMS_TO_TICKS(2)) == pdTRUE) {
      if (std::memcmp(f.mac, g_rtc.launcher_mac, proto::kMacLen) == 0 &&
          btn::isAckFor(f.data, f.len, g_rtc.key, seq)) {
        acked = true;
      }
    }
  }
}

void showFeedback(bool acked) {
  const btn::Feedback fb = btn::decideFeedback(acked, g_rtc.low_batt);
  if (fb.haptic_ms > 0) {
    haptic(true);
    led(true);
    delay(fb.haptic_ms);
    haptic(false);
    led(false);
  }
  if (fb.nack_blinks > 0) blink(fb.nack_blinks, cfg::kBtnNackBlinkOnMs, cfg::kBtnNackBlinkOffMs);
  if (fb.lowbatt_blinks > 0) {
    delay(150);
    blink(fb.lowbatt_blinks, cfg::kBtnLowBattBlinkOnMs, cfg::kBtnLowBattBlinkOffMs);
  }
}

// ---------------------------------------------------------------- pairing --
// Pairing: new random key (kept as "pending" in NVS until a launcher confirms,
// so a failed attempt never destroys a working pairing), PAIR_REQ broadcast every
// 500 ms for up to 30 s, PAIR_ACK must be signed with the new key.
bool doPairing(uint16_t batt_mv, bool radio_up) {
  if (!radio_up && !radioInit()) return false;
  addPeer(kBroadcast);
  uint8_t new_key[proto::kKeyLen];
  for (size_t i = 0; i < proto::kKeyLen; i += 4) {
    const uint32_t r = esp_random();
    std::memcpy(new_key + i, &r, 4);
  }
  g_prefs.putBytes("pkey", new_key, sizeof(new_key));
  const uint32_t req_seq = nextSeq();
  uint8_t req[proto::kPacketLen];
  proto::pack(proto::makePairReq(req_seq, batt_mv, new_key), new_key, req);

  btn::PairingSchedule sched;
  const uint32_t t0 = millis();
  sched.start(t0);
  for (;;) {
    const uint32_t now = millis();
    led(((now - t0) % cfg::kBtnPairBlinkPeriodMs) < cfg::kBtnPairBlinkPeriodMs / 2);
    const btn::PairingSchedule::Action a = sched.poll(now);
    if (a == btn::PairingSchedule::Action::Timeout) break;
    if (a == btn::PairingSchedule::Action::SendReq) esp_now_send(kBroadcast, req, sizeof(req));
    RxFrame f;
    if (xQueueReceive(g_rxq, &f, pdMS_TO_TICKS(5)) == pdTRUE && btn::isPairAckFor(f.data, f.len, new_key, req_seq)) {
      std::memcpy(g_rtc.key, new_key, sizeof(new_key));
      std::memcpy(g_rtc.launcher_mac, f.mac, proto::kMacLen);
      g_rtc.paired = true;
      g_prefs.putBytes("key", g_rtc.key, sizeof(g_rtc.key));
      g_prefs.putBytes("lmac", g_rtc.launcher_mac, sizeof(g_rtc.launcher_mac));
      g_prefs.putBool("paired", true);
      g_prefs.remove("pkey");
      led(false);
      for (int i = 0; i < 2; ++i) {  // success: two haptic pulses
        haptic(true);
        delay(cfg::kBtnHapticPulseMs);
        haptic(false);
        delay(120);
      }
      return true;
    }
  }
  g_prefs.remove("pkey");
  led(false);
  blink(cfg::kBtnNackBlinks, cfg::kBtnNackBlinkOnMs, cfg::kBtnNackBlinkOffMs);
  return false;
}

// Blocks while the switch is held; true once it has been held >= 5 s.
bool heldForLongPress() {
  btn::PressTracker t;
  t.begin(true, millis());
  for (;;) {
    switch (t.update(switchPressed(), millis())) {
      case btn::PressTracker::Event::LongPress: return true;
      case btn::PressTracker::Event::Released: return false;
      case btn::PressTracker::Event::None: break;
    }
    delay(5);
  }
}

// ------------------------------------------------------------------ sleep --
[[noreturn]] void sleepNow() {
  led(false);
  haptic(false);
  g_prefs.end();
  // Wait for a clean release so the LOW-level wake does not fire again at once.
  const uint32_t t0 = millis();
  uint32_t high_since = millis();
  bool stuck = false;
  for (;;) {
    if (switchPressed()) high_since = millis();
    if (millis() - high_since >= cfg::kBtnReleaseDebounceMs) break;
    if (millis() - t0 >= cfg::kBtnStuckReleaseMs) {
      stuck = true;
      break;
    }
    delay(2);
  }
  // Keep the LED and the motor transistor off while asleep.
  gpio_hold_en(static_cast<gpio_num_t>(kPinLed));
  gpio_hold_en(static_cast<gpio_num_t>(kPinHaptic));
  gpio_deep_sleep_hold_en();
  if (stuck) {
    // Switch stuck closed: a LOW-level wake would loop. Check again later.
    esp_sleep_enable_timer_wakeup(static_cast<uint64_t>(cfg::kBtnStuckSleepMs) * 1000ULL);
  } else {
    esp_deep_sleep_enable_gpio_wakeup(1ULL << kPinSwitch, ESP_GPIO_WAKEUP_GPIO_LOW);
  }
  esp_deep_sleep_start();
  for (;;) {
  }
}

}  // namespace

void setup() {
  gpio_hold_dis(static_cast<gpio_num_t>(kPinLed));
  gpio_hold_dis(static_cast<gpio_num_t>(kPinHaptic));
  gpio_deep_sleep_hold_dis();
  pinMode(kPinLed, OUTPUT);
  pinMode(kPinHaptic, OUTPUT);
  led(false);
  haptic(false);
  pinMode(kPinSwitch, INPUT);  // external 1 MOhm pull-up

  const esp_sleep_wakeup_cause_t cause = esp_sleep_get_wakeup_cause();
  const bool woke_by_press = cause == ESP_SLEEP_WAKEUP_GPIO;
  const bool warm = woke_by_press || cause == ESP_SLEEP_WAKEUP_TIMER;
  const bool pressed = switchPressed();

  loadState(warm);

  // Power-up, or the timer re-check of a held/stuck switch: never fire. A held switch keeps the
  // timer wake; a released one re-arms the GPIO wake, so only the NEXT real press can fire.
  if (!woke_by_press) sleepNow();
  (void)pressed;

  const uint16_t batt_mv = readBatteryMv();  // before the radio draws current spikes
  g_rtc.low_batt = btn::updateLowBattery(g_rtc.low_batt, batt_mv);

  bool radio_up = false;
  if (btn::shouldSendFire(btn::Wake::Press, g_rtc.paired)) {
    radio_up = radioInit();
    const bool acked = radio_up && sendFire(batt_mv);
    showFeedback(acked);
  }

  if (switchPressed()) {
    if (heldForLongPress()) {
      doPairing(batt_mv, radio_up);
    } else if (!g_rtc.paired) {
      led(true);
      delay(cfg::kBtnUnpairedBlinkMs);
      led(false);
    }
  } else if (!g_rtc.paired) {
    led(true);
    delay(cfg::kBtnUnpairedBlinkMs);  // unpaired: one long blink
    led(false);
  }
  sleepNow();
}

void loop() { sleepNow(); }
