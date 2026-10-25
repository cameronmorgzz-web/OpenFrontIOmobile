// Beer Launcher firmware (ESP32-C3 SuperMini).
//
// A 1 kHz control task samples the hardware, ticks the state machine
// (../common/src/launcher_sm.*) and applies its outputs. loop() handles the radio
// (ESP-NOW, channel 1), NVS persistence and the USB serial console, so slow NVS
// writes never delay a control tick. The state machine is shared under a mutex.
//
// Serial console (115200, USB CDC): status | fire | decock | pair | clear | help

#include <Arduino.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_arduino_version.h>
#include <esp_now.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/semphr.h>
#include <freertos/task.h>

#include <cstring>

#include "config.h"
#include "hal_esp32.h"
#include "launcher_sm.h"
#include "protocol.h"

using namespace beer;
using launcher::LauncherSM;
using launcher::State;

namespace {

constexpr const char* kNvsNs = "beerlnch";

struct RxFrame {
  uint8_t mac[proto::kMacLen];
  uint8_t len;
  uint8_t data[proto::kPacketLen];
};

LauncherSM g_sm;
SemaphoreHandle_t g_lock = nullptr;
QueueHandle_t g_rxq = nullptr;
Preferences g_prefs;

struct Lock {
  Lock() { xSemaphoreTake(g_lock, portMAX_DELAY); }
  ~Lock() { xSemaphoreGive(g_lock); }
  Lock(const Lock&) = delete;
  Lock& operator=(const Lock&) = delete;
};

// ------------------------------------------------------------ control task --
void controlTask(void*) {
  TickType_t wake = xTaskGetTickCount();
  for (;;) {
    {
      Lock l;
      g_sm.tick(hal::readInputs(), millis());
      hal::apply(g_sm.outputs());
    }
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(1) > 0 ? pdMS_TO_TICKS(1) : 1);
  }
}

// ------------------------------------------------------------------ radio --
#if ESP_ARDUINO_VERSION_MAJOR >= 3
void onRecv(const esp_now_recv_info_t* info, const uint8_t* data, int len) {
  const uint8_t* mac = info->src_addr;
#else
void onRecv(const uint8_t* mac, const uint8_t* data, int len) {
#endif
  if (g_rxq == nullptr || len <= 0 || len > static_cast<int>(proto::kPacketLen)) return;
  RxFrame f;
  std::memcpy(f.mac, mac, sizeof(f.mac));
  f.len = static_cast<uint8_t>(len);
  std::memcpy(f.data, data, static_cast<size_t>(len));
  xQueueSend(g_rxq, &f, 0);
}

void ensurePeer(const uint8_t mac[proto::kMacLen]) {
  if (esp_now_is_peer_exist(mac)) return;
  esp_now_peer_info_t peer;
  std::memset(&peer, 0, sizeof(peer));
  std::memcpy(peer.peer_addr, mac, proto::kMacLen);
  peer.channel = cfg::kEspNowChannel;
  peer.ifidx = WIFI_IF_STA;
  peer.encrypt = false;
  esp_now_add_peer(&peer);
}

void radioInit() {
  g_rxq = xQueueCreate(16, sizeof(RxFrame));
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(cfg::kEspNowChannel, WIFI_SECOND_CHAN_NONE);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_recv_cb(onRecv);
}

// ----------------------------------------------------------- persistence --
void loadPersisted(launcher::PairingRecord* pr, uint32_t* last_seq) {
  g_prefs.begin(kNvsNs, false);
  pr->valid = g_prefs.getBool("paired", false);
  if (pr->valid) {
    const size_t m = g_prefs.getBytes("bmac", pr->mac, sizeof(pr->mac));
    const size_t k = g_prefs.getBytes("key", pr->key, sizeof(pr->key));
    pr->valid = (m == sizeof(pr->mac) && k == sizeof(pr->key));
  }
  *last_seq = g_prefs.getUInt("lastseq", 0);
}

void persist(const launcher::PersistRequest& req, uint32_t last_seq, const launcher::PairingRecord& pr) {
  if (req.pairing) {
    g_prefs.putBytes("bmac", pr.mac, sizeof(pr.mac));
    g_prefs.putBytes("key", pr.key, sizeof(pr.key));
    g_prefs.putBool("paired", pr.valid);
  }
  if (req.last_seq) g_prefs.putUInt("lastseq", last_seq);
}

void printMac(const uint8_t* m) {
  Serial.printf("%02X:%02X:%02X:%02X:%02X:%02X", m[0], m[1], m[2], m[3], m[4], m[5]);
}

// --------------------------------------------------------------- console --
void printStatus() {
  launcher::Inputs in = hal::readInputs();
  Lock l;
  Serial.printf("state=%s fault=%s last_fault=%s msg=\"%s\"\n", launcher::stateName(g_sm.state()),
                launcher::faultName(g_sm.fault()), launcher::faultName(g_sm.lastFault()), g_sm.message());
  Serial.printf("in: arm_home=%d arm_cocked=%d ring_home=%d pin_in=%d test=%d mag_empty=%d can_in_cup=%d enc=%lu\n",
                in.arm_home, in.arm_cocked, in.ring_home, in.safety_pin_in, in.test_button, in.mag_empty,
                in.can_in_cup, static_cast<unsigned long>(in.enc_edges));
  Serial.printf("ring_pos=%ld (%s) hold=%d target=%ld stroke=%lu edges, can_preloaded=%d mag_empty_flag=%d\n",
                static_cast<long>(g_sm.ringPosition()), g_sm.ringPositionKnown() ? "known" : "unknown", g_sm.holding(),
                static_cast<long>(g_sm.holdTarget()),
                static_cast<unsigned long>(g_sm.cockStrokeEdges()), g_sm.canPreloaded(), g_sm.magEmptyFlag());
  Serial.print("paired=");
  Serial.print(g_sm.pairing().valid ? "yes " : "no ");
  if (g_sm.pairing().valid) printMac(g_sm.pairing().mac);
  const launcher::RadioStats& s = g_sm.radioStats();
  Serial.printf(" last_seq=%lu button_batt=%umV\n", static_cast<unsigned long>(g_sm.lastSeq()),
                g_sm.lastButtonBattMv());
  Serial.printf("radio: accepted=%lu dup=%lu stale=%lu bad_frames=%lu bad_tags=%lu unknown=%lu\n",
                static_cast<unsigned long>(s.accepted), static_cast<unsigned long>(s.duplicates),
                static_cast<unsigned long>(s.stale), static_cast<unsigned long>(s.bad_frames),
                static_cast<unsigned long>(s.bad_tags), static_cast<unsigned long>(s.unknown_sender));
}

void handleCommand(const char* cmd) {
  if (std::strcmp(cmd, "status") == 0) {
    printStatus();
    return;
  }
  bool ok = false;
  const char* what = "";
  {
    Lock l;
    const uint32_t now = millis();
    if (std::strcmp(cmd, "fire") == 0) {
      const proto::AckResult r = g_sm.trigger(launcher::TriggerSource::Serial, now);
      ok = r == proto::AckResult::Accepted;
      what = g_sm.message();
    } else if (std::strcmp(cmd, "decock") == 0) {
      ok = g_sm.requestDecock(now);
      what = g_sm.message();
    } else if (std::strcmp(cmd, "pair") == 0) {
      ok = g_sm.requestPairing(now);
      what = ok ? "pairing window open (30 s)" : "pairing only from IDLE";
    } else if (std::strcmp(cmd, "clear") == 0) {
      ok = g_sm.requestClear(now);
      what = g_sm.message();
    } else {
      Serial.println("commands: status | fire | decock | pair | clear");
      return;
    }
    hal::apply(g_sm.outputs());
  }
  Serial.printf("%s: %s %s\n", cmd, ok ? "ok" : "refused", what);
}

void pollSerial() {
  static char line[32];
  static size_t n = 0;
  while (Serial.available() > 0) {
    const int c = Serial.read();
    if (c == '\r' || c == '\n') {
      if (n > 0) {
        line[n] = '\0';
        handleCommand(line);
        n = 0;
      }
    } else if (n + 1 < sizeof(line)) {
      line[n++] = static_cast<char>(c);
    }
  }
}

State g_logged_state = State::Idle;

}  // namespace

void setup() {
  hal::begin();  // warning output off as early as possible
  Serial.begin(115200);
  g_lock = xSemaphoreCreateMutex();

  launcher::PairingRecord pr;
  uint32_t last_seq = 0;
  loadPersisted(&pr, &last_seq);
  radioInit();

  {
    Lock l;
    g_sm.begin(hal::readInputs(), millis(), pr, last_seq);
    hal::apply(g_sm.outputs());
    g_logged_state = g_sm.state();
  }
  Serial.print("Beer Launcher up. MAC ");
  Serial.println(WiFi.macAddress());
  printStatus();

  xTaskCreate(controlTask, "ctrl", 4096, nullptr, configMAX_PRIORITIES - 2, nullptr);
}

void loop() {
  RxFrame f;
  while (xQueueReceive(g_rxq, &f, 0) == pdTRUE) {
    launcher::TxFrame tx;
    launcher::PersistRequest req;
    uint32_t last_seq;
    launcher::PairingRecord pr;
    {
      Lock l;
      g_sm.onPacket(f.mac, f.data, f.len, millis(), &tx);
      hal::apply(g_sm.outputs());  // a trigger starts the motor + beacon right away
      req = g_sm.takePersist();
      last_seq = g_sm.lastSeq();
      pr = g_sm.pairing();
    }
    if (tx.send) {
      ensurePeer(tx.dest);
      esp_now_send(tx.dest, tx.data, tx.len);
    }
    persist(req, last_seq, pr);  // outside the lock: NVS writes can take ms
  }

  pollSerial();

  State s;
  launcher::FaultCode fc;
  const char* msg;
  {
    Lock l;
    s = g_sm.state();
    fc = g_sm.fault();
    msg = g_sm.message();
  }
  if (s != g_logged_state) {
    Serial.printf("[%lu] %s -> %s %s %s\n", static_cast<unsigned long>(millis()), launcher::stateName(g_logged_state),
                  launcher::stateName(s), fc != launcher::FaultCode::None ? launcher::faultName(fc) : "", msg);
    g_logged_state = s;
  }
  delay(1);
}
