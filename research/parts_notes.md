# Parts sourcing: hobby build, Milan (IT)

**Date prices were seen:** 2026-10-25 (all rows). Prices come from search-engine snapshots, so the page may have been indexed some days earlier.

## How this was gathered, and its limits (read first)

- This environment's egress proxy **refused direct connections** to `aliexpress.com`, `amazon.it` and every other shop (WebFetch failed with DNS errors, and curl got CONNECT 403). No product page could be opened directly.
- Every price and spec below comes from **WebSearch result snippets** of the listing pages, restricted to `aliexpress.*`, `amazon.it`, `federnshop.com` and similar sites. The snippets are taken verbatim where possible.
- **AliExpress prices:** search results mostly come back from the `aliexpress.us` mirror, so they are in **USD**, not EU/IT pricing. An approximate EUR value is given at an *assumed* 1 USD ≈ 0.90 EUR, marked "≈". Italian checkout prices on AliExpress (VAT included, Choice shipping) will differ, so check them in the app. Item IDs work on `it.aliexpress.com/item/<id>.html`. A `3256…` or `2251…` ID from the .us mirror normally maps to the global `1005…` or `3…` ID, so open the URL as given.
- **"unverified"** means the number was not visible in a snippet tied unambiguously to that exact listing or variant. The note says how the estimate was derived.
- Marketplace specs, especially torque and spring force, are seller claims and are often inconsistent. Where a manufacturer or catalogue source exists (Gutekunst, Omron, Mean Well, PMD, Hiwonder), it is listed in the table.

---

## 1. ESP32-C3 SuperMini (x2)

| source | URL | price (EUR) | pack qty | key specs (verbatim / as listed) |
|---|---|---|---|---|
| AliExpress (TENSTAR ROBOT) | https://www.aliexpress.com/item/1005006406538478.html | unverified, ≈ €1–4.50/pc (search snippets showed "around $1 each" and TENSTAR at "$4.82") | 1 (variants) | "ESP32-C3 SuperMini WiFi Bluetooth"; welded/unwelded options |
| AliExpress (generic) | https://www.aliexpress.us/item/3256810456857645.html | unverified (≈ $1 class) | 1 | "ESP32-C3 SuperMini Development Board, WiFi Bluetooth Module" |
| Amazon.it (iHaospace) | https://www.amazon.it/dp/B0D1YD8FGQ | price not shown in snippet (unverified) | 3 | "ESP32-C3FN4 Built-in 4MB Flash" |
| Amazon.it (single) | https://www.amazon.it/dp/B0FR91DDGB | **€12.22** | 1 | "SuperMini ESP32-C3 … 4MB Flash WiFi+Bluetooth" |
| Amazon.it (TECNOULAB) | https://www.amazon.it/dp/B0DF5B8SCT | €24.10 (board + expansion board); 2-pack "from €13.92" | 1 set | ESP32-C3 + SuperMini expansion board (LiPo charging) |

Specs from Amazon.it listing text for this board family: "blue LED on GPIO8"; "deep-sleep current … about 43 µA"; "400KB SRAM, 384KB ROM, 4M flash"; 22.5 × 18 mm.
- **LDO:** ME6211-series 3.3 V/500 mA is what community pinout docs report (mischianti.org). **No listing states it, so treat it as unverified.**
- **Deep sleep:** the 43 µA is a seller claim. A community write-up reports about 100–500 µA real-world because of LDO quiescent current and the LEDs. Check that the chip is marked **FN4/FH4**, since non-flash "ESP32-C3" clones exist.

---

## 2. TP4056 USB-C 1S charger with DW01A + 8205A

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/1005005315322989.html | ≈ €1.00 ($1.09 typical, from snippet) | 1 | "TP4056 1A Type-C USB Lithium Battery Charging Module" (dual protection) |
| AliExpress | https://www.aliexpress.us/item/3256807698672343.html | unverified; bulk ≈ $0.22/pc | 1–100 | "TP4056 1A … TYPE-C USB Interface Charging Protection Two-in-one" |
| AliExpress | https://www.aliexpress.us/item/3256803744299324.html | unverified | 5 | "5PCS TP4056 5V 1A Charger Module with Protection" |
| Amazon.it | https://www.amazon.it/dp/B0F5BS8DCS | **€12.68** | 2 | "TP4056 + DW01 … 1A Current USB-C"; Output 4.2 V, Input 8 V (max), 1 A |
| Amazon.it (StarMaker) | https://www.amazon.it/dp/B0D9TSG6VB | **€7.99** | 5 | "TP4056 USB C … 5V 1A … Short Circuit Protection … Anti Deep Discharge" |
| Amazon.it (AZDelivery) | https://www.amazon.it/dp/B0CBKKSYRQ | €8.99 | 5 | TP4056 module. Check that the variant has USB-C and protection |

- **Charge current:** 1 A, set by the PROG resistor (1.2 kΩ). For a 400–600 mAh cell, swap R_PROG to about 2.4–3 kΩ (≈ 0.5–0.4 A, per the TP4056 datasheet formula) to stay at or below 1C.
- **Battery-side leakage:** TP4056 is "< 2 µA when input removed" (LCSC datasheet text). The DW01A + 8205A adds its own quiescent current: about 3 µA typical per the DW01A datasheet (unverified, since the snippet did not confirm it). Measured module drain can be far higher; one forum report saw 1.6 mA on a clone layout. Measure your module.
- **Better alternatives:**
  - MCP73831 module (500 mA, Micro-USB): https://www.aliexpress.com/item/1005004215775924.html ($0.99–1.71). Its protection must come from the cell's own PCM.
  - Keep the TP4056 + DW01A and change R_PROG.
  - Avoid IP5306 or other power-bank SoCs, which have mA-level quiescent current.

---

## 3. 1S LiPo, 3.7 V, 400–1000 mAh, protected, fits a ~60 mm puck

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.us/item/2251832628547931.html | ≈ €6.90–7.10 ($7.64–7.90 snippet) | 1 | "3.7V 500mAh … LiPo … 503035 + JST PH 2.0mm 2Pin" |
| AliExpress | https://www.aliexpress.us/item/2251832808704320.html | unverified | 1 | "503035 JST 2pin 1.0/1.25/1.5/2.0/2.54mm connector" |
| Amazon.it | https://www.amazon.it/dp/B0CRKY8RC7 | unverified (not in snippet) | 1 | "3.7 V 500 mAh 503035 … 2P PH 2.0 mm … JST"; listed dims **35 × 30 × 6 mm** |
| Amazon.it (RAEWSTCO) | https://www.amazon.it/dp/B0CM8WXZZG | unverified | 2 | "3.7V 1000mAh 803040 Lipo … JST" |
| Amazon.it | https://www.amazon.it/dp/B0DPZLNQ2C | unverified | 1 | "1000mAh 803040 … Micro PH1.25 … Built-in Protection Circuit"; max discharge ≈ 1 A |
| Amazon.it (Seamuing) | https://www.amazon.it/dp/B09B77CC7L | unverified | 4 | "3.7V 1000mAh 1S 1C … with Protection Board … Micro JST1.25 … for ESP32" |

- **Sizes:** the code is T×W×L in 0.1 mm/mm, which is a naming convention and was not checked against each listing. 503035 = 5 × 30 × 35 mm, 602535 = 6 × 25 × 35 mm, 803040 = 8 × 30 × 40 mm. All fit inside a 60 mm puck.
- **Connector polarity:** the PH1.25 and PH2.0 versions are not interchangeable, and JST polarity varies between sellers. Check it before connecting.

---

## 4. 16 mm metal momentary pushbutton (and 12 mm)

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/32867071630.html | ≈ €0.45 ("0.49US $ 25% OFF" in title) | 1 | "16mm Metal Push Button Switch IP67 Waterproof Nickel Plated Brass … Self reset 1NO High/Flat … Momentary"; 12 mm and 19/22 mm variants on the same seller |
| AliExpress | https://www.aliexpress.us/item/3256808011741253.html | unverified | 1 | "Waterproof IP66 16mm Metal Push Button Momentary" |
| Amazon.it (8 pcs) | https://www.amazon.it/dp/B0DPSDCNGS | **€10.38** (≈ €1.30/pc) | 8 | "16mm Momentary … Screw Terminals … 2A 12V/24V/125V/250V AC Stainless Steel"; IP65, IK10 |
| Amazon.it (TankerStreet) | https://www.amazon.it/dp/B07C6412X6 | unverified | 4 | "16mm Stainless Steel … Flat Top Waterproof"; IP67, 3 A 250 VAC |
| Amazon.it (Gebildet, LED) | https://www.amazon.it/dp/B07VN3G826 | €9.99 | 2 | "16 mm Momentary … Stainless Steel, 12 V-24 V 5 A LED 1NO1NC" |

**Stroke and actuation force:** not published in any snippet, so both are unverified. Typical datasheets for this style give a stroke of about 1–2 mm, but no listing confirms it. If force matters, ask the seller or measure it.

---

## 5. Small compression springs for the button cap (~1 N at a few mm)

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.us/item/3256802345180704.html | unverified | 10 per size | "0.6 mm Compression Springs … Wire Dia 0.6 mm Outer Dia 4 5 6 7 8 9 10 11 12 mm Length 5 10 15 20 25 - 100 mm" |
| AliExpress | https://www.aliexpress.us/item/3256805837247982.html | unverified | per size | "Wire Diameter 0.8mm 304 Stainless … OD 5/6/7/8/9/10/11/12/13/14mm Length 5 8 10 12 15-305mm" |
| AliExpress | https://www.aliexpress.us/item/2251832836179204.html | unverified | 10–20 | "0.8mm compression spring outer diameter 5–10mm Stainless" |
| Amazon.it (CREEYA) | https://www.amazon.it/dp/B092R6CK89 | no offer shown (unverified) | 225 (15 sizes) | "Wire Diameter 0.6 mm 0.8 mm 1 mm, Outer Diameter 8 mm 9 mm 9.5 mm, Length 10 mm 20 mm 50 mm" |
| Gutekunst (compression catalogue) | https://www.federnshop.com/en/products/compression_springs.html | per part | single units | Publishes R (N/mm), Fn and Ln per part number. This is the best option if you need a known rate |

**Estimate (not from a listing):** a 0.6 × 10 × 15 mm stainless spring with about 6 active coils works out near 0.2–0.3 N/mm by the standard spring formula. That gives roughly 1 N at 3–5 mm deflection. Treat it as a rough estimate.

---

## 6. STEEL EXTENSION springs with hooks (critical)

Target: wire 1.5–2.5 mm, OD 12–20 mm, L0 60–150 mm, max load ≥ 120 N.

### (c) Gutekunst Federn (federnshop.com): best pick, full published data, single units, ships to IT

Shipping to Italy is shown as **€8.55** in the site's structured data, with 3–7 days handling and 3–14 days transit. That figure comes from markup, not a shipping table, so it is unverified. No minimum order. Material for the Z- parts is EN 10270-1 spring steel; RZ- parts are 1.4310 stainless. The listed price does not say whether VAT is included (check at checkout).

| part | URL | price (EUR, unit) | d × De × L0 (mm) | R (N/mm) | F0 initial (N) | Fn max (N) | sn max travel (mm) | Ln (mm) | notes |
|---|---|---|---|---|---|---|---|---|---|
| **Z-140AI** | https://www.federnshop.com/en/products/extension_springs/z-140ai.html | 6.23 (1), 3.92 (2), 2.53 (3), 2.11 (7) | 2 × 18 × 87.4 | 1.263 | 11.81 | **149.2** | 108.82 | blank on page (≈ 196 = L0 + sn, derived) | 180° loops; 41.6 g |
| **Z-141HI** | https://www.federnshop.com/en/products/extension_springs/z-141hi.html | 6.56 (1), 4.13 (2), 2.93 (3) | 2 × 16 × 121 | 1.2 | 14.5 | **166.7** (±9.21) | 126.84 | 247.84 | 180° loops; L0 tolerance ±2 mm |
| **Z-147K-01X** | https://www.federnshop.com/en/products/extension_springs/z-147k-01x.html | 6.40 (1); 0.69 from 75 pcs | 2.2 × 20 × 90.9 | 1.472 | 14.71 | **176.1** | 109.67 | (≈ 200.6 derived) | 270° loops |
| **Z-162X** | https://www.federnshop.com/en/products/extension_springs/z-162x.html | 6.56 (1); 2.50 from 7 pcs | 2.5 × 15 × 118 | 5.126 | 29.41 | **324.5** (±24.98) | 57.56 | (≈ 175.6 derived) | stiff and short travel; 63.26 g |
| RZ-162X (stainless) | https://www.federnshop.com/de/produkte/zugfedern/rz-162x.html | 7.04 (1); 2.95 at qty | 2.5 × 15 × 118 | 4.402 | n/a | 269.8 (±24.16) | n/a | n/a | 1.4310, 200 °C limit |

All rows check out: F0 + R·sn = Fn for Z-140AI, Z-141HI, Z-147K-01X and Z-162X. Related parts: Z-140I (same d/De but shorter, R 2.041), RZ-140I and RZ-140AI (stainless, Fn 125.1 N), RZ-141HI (stainless, R 1.031, Fn 139.7). A German eBay seller (th-mini) also resells Gutekunst RZ parts with the data in the title, e.g. https://www.ebay.de/itm/124367121379 ("2,5mm … 20x123,5mm 21,2kg").

**Lee Spring / Misumi:** Lee Spring publishes rate, max load and initial tension per LE part in its UK catalogue (https://www.leespring.co.uk/sites/default/files/2020-01/Extension_Springs_Lee_Spring_UK_Eng.pdf), but no specific part with a price was confirmed. Misumi EU was not reachable via search. Gutekunst is the practical choice.

### (a) AliExpress: no rate or max load is published; geometry only

| source | URL | price (EUR) | pack qty | key specs (verbatim) |
|---|---|---|---|---|
| AliExpress (hkdzFastener) | https://www.aliexpress.com/i/33004227563.html | ≈ €3.40–4.20 ($3.75–4.69) | 1 | "Wire Diameter 2mm Tension Spring With Hooks Steel … Outer Diameter 15mm Length 50 100mm" |
| AliExpress | https://www.aliexpress.us/item/3256810340568996.html | ≈ €0.90 ($0.99, probably the lowest variant) | 1 | "Wire Diameter 2.5mm With Hook Extension Tension Spring"; OD options include 16 and 20 mm; lengths seen 45/60/260 mm |
| AliExpress | https://www.aliexpress.us/item/3256806586685203.html | ≈ €4.35 ($4.84/pc) | 1 | "304 Stainless Steel Double Loop … Extension Spring"; 2.0 mm wire, OD 14/17/20 mm, L 80–200 mm |

**None of these publish spring rate or max load.** 304 stainless at the same geometry carries about 17% less load than music wire (Lee Spring 0.833 factor).

### (b) Amazon.it

| source | URL | price (EUR) | pack qty | key specs (verbatim) |
|---|---|---|---|---|
| GUNGY | https://www.amazon.it/dp/B0CN937VD6 | ~€9.99 (unverified: seen in a "frequently bought together" block) | 2 | "80mm … Acciaio Inossidabile Diametro Filo 2,5mm Diametro Esterno 18mm Tiro 12,8kg" (≈ 125.6 N). A 100 mm version is listed at €13.59 (2 pcs) |
| GUNGY | https://www.amazon.it/dp/B0CN95MXP4 | ~€8.79 (unverified, same method) | 2 | "60 mm … Wire Diameter 2 mm Outer Diameter 16 mm Pull 8.8 kg" (86.3 N, **below the 120 N target**); 70 and 100 mm versions €11.99 |
| GUNGY | https://www.amazon.it/dp/B0D4796H9Q | unverified | 2 | "50 mm … Wire Diameter 2.5 mm External Diameter 16 mm Pull 19 kg" (L0 below 60 mm) |
| CREEYA kit | https://www.amazon.it/dp/B0D1PCLZ66 | **€12.81** | 10 (5 sizes × 2) | "Length 5cm 6cm 8cm 10cm 12cm, Wire Diameter 2mm, Outer Diameter 16mm, Stainless … 12kg" |
| eROOSY | https://www.amazon.it/dp/B0CPS88V33 | unverified | 2 | "2.5 * 20 * 100mm … 65Mn" (spring steel) |
| UYUYong | https://www.amazon.it/dp/B09WMBWM65 | unverified | 2 | "2,5 * 20 * 150mm" |

---

## 7. 12 V DC gearmotor with Hall encoder (60–150 rpm)

**Power reality check (my arithmetic from the published numbers):**

| option | output at the rated point | rated current × 12 V |
|---|---|---|
| JGB37-520 | 0.255 N·m × 85 rpm ≈ **2.3 W** | n/a |
| JGB37-545 (56:1) | 0.44 N·m × 95 rpm ≈ **4.4 W** | 12 W input |
| 37GB555 (30:1) | 0.98 N·m × 100 rpm ≈ **10.3 W** | n/a |

Only the 555-class motor gets near "12 W output". For a true ≥ 12 W output you likely need a 555 or 775-size motor, or a larger GM37-555/42 mm gearmotor.

### Option A: JGB37-520, 12 V, 1:90 (110 rpm) with Hall encoder (lowest power)

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/1005005954131759.html | ≈ €10.50–10.80 ($11.59–11.95; which speed variant the snippet price belongs to is unverified) | 1 | "JGB37-520 Hall Encoder … 6V12V … 6RPM~1590RPM With Speed Measurement" |
| AliExpress | https://www.aliexpress.us/item/3256807403055518.html | unverified | 1 | "JGB37-520 DC 12V Gear Motor And Encoder Mounting Bracket Coupling Wheel" |
| Amazon.it | https://www.amazon.it/dp/B0GXT43VX7 | **€13.94** | 1 | "Motoriduttore 12V DC JGB37 520 … uscita codificatore a quadratura"; rated speed 140 rpm |
| Amazon.it | https://www.amazon.it/dp/B0CKMC8MSF | unverified | 1 | "JGB37 520 … con Encoder Hall … Kit Staffa Ruota" |

Reference spec table for the 12 V, 110 rpm variant (Hiwonder official page, https://www.hiwonder.com/products/hall-encoder-dc-geared-motor):

| ratio | no-load rpm | rated rpm | rated torque | stall torque | rated current | stall current | encoder |
|---|---|---|---|---|---|---|---|
| 1:90 | 110 | 85 | 2.6 kg·cm | 15 kg·cm | not retrieved | 3.2 A | 11 PPR on the motor shaft, AB phase (Hiwonder forum) → ≈ 990 PPR output, 3960 counts with x4 decoding (derived) |

A Ram-E-Shop 110 rpm set lists rated torque 10 kg·cm, max 15 kg·cm, rated current ≤ 1 A and stall current 2.3 A. That conflicts with Hiwonder, so trust Hiwonder.

### Option B: JGB37-545 with encoder, 12 V (mid power)

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.us/item/3256808307951430.html | ≈ €4.60–10.60 ($5.09–11.73 across variants; unverified per variant) | 1 | "JGB37-545 DC 12V 24V High Torque encoder Gear Motor … 8/12/23/37/47/70/110/200/330/625/1000RPM" |
| PMD (spec source, sells direct) | https://precisionminidrives.com/product/37mm-dc-gear-motor-with-encoder-82mm-type-model-nfp-jgb37-545-en | price not retrieved | 1 | NFP-JGB37-545-EN |

PMD 12 V spec table (NFP-JGB37-545-EN):

| ratio | no-load rpm / current | rated rpm / current | rated torque | stall torque / current |
|---|---|---|---|---|
| 56:1 | 110 rpm / 0.2 A | 95 rpm / 1 A | 4.5 kg·cm | 35 kg·cm / 5 A |
| 90:1 | 70 rpm / 0.2 A | 58 rpm / 1 A | 7.2 kg·cm | 35 kg·cm / 5 A |

- The page header says 0.4 A no-load, which conflicts with the table.
- Ratios of about 70:1 and above are marked "Forbid Stall".
- Encoder PPR was not retrieved for the 545. The sibling 3530-EN lists 16 PPR.

### Option C: 37GB555 with encoder, 12 V, 30:1 (highest power, ≈ 13 W)

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| Digiware (spec source) | https://digiwarestore.com/en/product-categories/motor-dc-gearbox-encoder-high-torque-37gb555-713499.html | not EU (Indonesian shop) | 1 | 12 VDC, **133 rpm no-load, rated 10 kg·cm at 100 rpm, 1.5 A, 13 W, 30:1** (stall values and PPR not given) |
| AliExpress (plain, no encoder) | https://www.aliexpress.us/item/3256801126522235.html | unverified | 1 | "XD-37GB555 … 12V/24V 15W High Torque … 10RPM-600RPM" |
| AliExpress (planetary with encoder) | https://www.aliexpress.us/item/3256805567772710.html | unverified | 1 | "36mm DC Gear Motor Planetary … 12V 24V With Encoder 36GP-555 … 15W" |

- Handsontec's datasheet for the 600 rpm XD-37GB555 gives 3 A stall at 12 V (https://handsontec.com/dataspecs/motor_fan/XD-37GB555.pdf).
- **No AliExpress 37GB555 with a Hall encoder at about 100 rpm was confirmed.** Ask the seller before ordering.

---

## 8. DRV8871 motor driver

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (TENSTAR) | https://www.aliexpress.com/item/1005009351232038.html | ≈ €1.85 ($2.03) | 1 | "DRV8871 H-Bridge Brushed DC Motor Driver Breakout Board PWM Control 3.6A Max Internal Current Sense 6.5V To 45V" |
| AliExpress | https://www.aliexpress.com/item/1005010191916956.html | ≈ €1.00 ($1.09 typical sale price) | 1 | "DRV8871 6.5-45V … 3.6A … Short-circuit Protection" |
| Amazon.it (Fafeicy) | https://www.amazon.it/dp/B08TCDL2G7 | **€10.27** | 1 | "DRV8871 BOB Drive Module 3.6A PWM" |
| Amazon.it (Adafruit) | https://www.amazon.it/dp/B01J9UZ31W | unverified | 1 | "Adafruit DRV8871 … 3.6A Max" |

- **3.6 A is the peak rating.** Continuous current is about 2 A or less without heatsinking (TI datasheet, from memory; unverified here).
- A JGB37-545 stalls at 5 A, which exceeds the DRV8871. The DRV8871 limits current itself through ILIM (current regulation), so set ILIM.
- **BTS7960 (43 A)** is the better choice for the 37GB555 or for stall-prone loads. TB6612 (1.2 A continuous) is too weak for these motors.

---

## 9. MG90S metal-gear servo (x2)

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (TZT) | https://www.aliexpress.us/item/2251832778440556.html | ≈ €1.25 ($1.38) | 1 | "TZT MG90S Metal gear Digital 9g Servo" |
| AliExpress (Racerstar) | https://www.aliexpress.com/i/33055695487.html | unverified | 2/4/6 | "Stall Torque: 1.8kg/cm (4.8V), 2.2kg/cm (6V); Operating Speed: 0.1sec/60degree (4.8v), 0.08sec/60degree (6v)" |
| Amazon.it (AZDelivery) | https://www.amazon.it/dp/B086V8RKZR | **€23.99** | 5 | 1.8 kg·cm at 4.8 V, 2.2 kg·cm at 6 V, metal gears |
| Amazon.it (VUNIVERSUM) | https://www.amazon.it/dp/B095YVLLFQ | unverified | 2 | "100% Metal Gears … 2 kg/cm at 4.8 V" |

- **Stall current is not published by sellers.** One article says "up to 650 mA under full load" (unverified). Budget about 0.7–1 A per servo at 5–6 V.
- A review of the mopei 2-pack (B06XQ7NPSS) reports plastic gears, so avoid it.

---

## 10. Buck converter 12 V → 5 V, ≥ 3 A

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/32261885063.html | ≈ €1.00 ($1.09–1.13) | 1 or 10 | "Ultra-Small … MP1584EN 3A Adjustable Buck Step Down" |
| AliExpress | https://www.aliexpress.us/item/3256806179603578.html | unverified ($0.99–3.70 seen) | 6 | "Mini MP1584EN DC-DC Buck Converter 3A" |
| Amazon.it (ARCELI) | https://www.amazon.it/dp/B07MY2XP21 | **€7.99** | 5 | "Ultra Small DC-DC 3A … 24V to 12V 9V 5V 3V" |
| Amazon.it (DollaTek) | https://www.amazon.it/dp/B07DJZMD26 | €5.99 | 1 | MP1584EN 3 A |
| Amazon.it (DollaTek XL4015) | https://www.amazon.it/dp/B081JP5YZP | unverified | 5 | "XL4015 5A DC-DC Buck Converter" |

- **Max current:** "3 A" is the MP1584EN peak. One seller advises "keep < 2.5 A for prolonged use".
- **For a real 3 A continuous 5 V rail (servos), choose the XL4015 (5 A).**

---

## 11. 12 V 3 A PSU (CE), DC jack, fuse

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| alimentatorishop.com (IT) | https://www.alimentatorishop.com/en/external-power-supplies/gst36e12-p1j-meanwell-power-supply-wallmount-36w-12v-input-100-240-vac | **€14.98 excl. VAT** (≈ €18.28 incl. 22% IVA, computed) | 1 | Mean Well GST36E12-P1J, 36 W, 12 V 3 A, Euro 2-pin, 5.5 × 2.1 × 11 mm plug |
| RS Italia | https://it.rs-online.com/web/p/alimentatori-cacc/1176586 | €36.39 incl. VAT (€29.83 excl.) | 1 | same part |
| Amazon.it | (GST36E12-P1J appears only as a related item, with no price) | unverified | — | Comparable: Mean Well GST40A12-P1J desktop unit https://www.amazon.it/dp/B083QH6BVJ (price unverified) |
| Amazon.it (DC jack) | https://www.amazon.it/dp/B08HGXYS4J | unverified | 5 | "5.5mm x 2.1mm DC Power Jack … Panel Mount … 3A … Threaded Nut" |
| AliExpress (DC jack) | https://www.aliexpress.com/item/1005005780993062.html | ≈ €1.00 ($1.09) | 10 | "DC-022B 3A 12v … Panel Mount Connector 5.5 mm x 2.1mm" |
| Amazon.it (fuses) | https://www.amazon.it/dp/B085N434K5 | unverified | 20 | "BOJACK F3AL250V 5x20mm 3A 250V Quick Fuses" |
| Amazon.it (inline holders + fuses) | https://www.amazon.it/dp/B07X8WL5TC | unverified | 10 holders + 100 fuses | "AGC Fuse Holder Inline Screw Type with 22 AWG … 5 x 20 mm" |
| AliExpress (inline holder) | https://www.aliexpress.us/item/2251832867812392.html | ≈ €1.00 ($1.09) | 10 | "5*20MM Glass Tube Fuse Holder Screw Type … 22 AWG Wire 250V" |
| Amazon.it (radial PTC) | https://www.amazon.it/dp/B0D9D86ZB7 | unverified | 50 | "Fusibile autoripristinante PTC RXEF 60V/72V … 3A …" (select the 3 A variant) |

**CE and efficiency (Mean Well):**
- DigiKey and Mouser list the GST36E12-P1J as "Efficiency Level VI". No-load power is < 0.075 W (Mean Well GST18/25/36 family page) or 75 mW max (DigiKey).
- Efficiency is about 87.5% typical at 12 V per the GST36E spec PDF (https://www.meanwell.com/Upload/PDF/GST36E/GST36E-SPEC.PDF), but the column alignment in the extract was ambiguous, so check the PDF.
- Distributors state "Compliant with EISA 2007, EU ErP". The **CE marking for this exact P/N was not explicitly confirmed** from a primary source. Mean Well's E-suffix (Euro-plug) models are sold in the EU with CE, but check the label or DoC.
- **Avoid unbranded AliExpress 12 V bricks for mains use.**

---

## 12. Micro limit switches with lever

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/1005006259880729.html | ≈ €1.00–2.10 ($1.09–2.33 seen) | 10 | "KW12 stroke limit switch … KW11-3Z-2 micro switch straight handle 3pin 5A 125V250V" |
| Amazon.it (RELAND SUN) | https://www.amazon.it/dp/B0B5PLGSFS | **€2.37** | 10 | "KW11-3Z a 3 pin 5A 250 V (con manico)" |
| Amazon.it (CESFONJER) | https://www.amazon.it/dp/B07SPX492J | unverified | 8 | "SS-5GL 5A 250V … 3 Pin Long Hinge Lever" |

- **Operating force:** generic KW11 listings do not publish it. The genuine **Omron SS-5GL** hinge lever is rated OF max **0.49 N (50 gf)** and RF min 0.06 N (Omron datasheet via alldatasheet and RS 682-2682).
- Clones are probably in the same range but unverified. Longer levers reduce the force.

---

## 13. TCRT5000 / IR break-beam

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (TZT) | https://www.aliexpress.us/item/3256801407533937.html | unverified (≈ $0.66–1.09 single in snippets) | 1/5 | "TCRT5000 Infrared Reflective IR Photoelectric Switch … Line Track Sensor Module" |
| AliExpress (break-beam, 3 mm) | https://www.aliexpress.com/w/wholesale-break-beam-sensors.html (search page; item ID not captured) | ≈ €1.00 ($1.09/set) | 4 pairs | "infrared circuit breaker sensors with 3mm LEDs … DC 3-5V … 100cm IR break beam" |
| AliExpress (bare diodes) | https://www.aliexpress.us/item/2255800122681148.html | unverified | 10 pairs | "3mm 5mm 940nm IR LED Infrared Emitter Receiver 10 Pairs" |
| Amazon.it (ANGEEK) | https://www.amazon.it/dp/B07Q81NTBX | **€9.99** | 5 | TCRT5000 module; detection distance "1–25 mm" |
| Amazon.it (LYEAA) | https://www.amazon.it/dp/B0CNHCHPNK | €3.24 | 1 | 3.3–5 V, sensitivity potentiometer |

**Range:** the TCRT5000 reflective sensor is about 1–25 mm (seller). Its peak sensitivity is about 2.5 mm per the Vishay datasheet (from memory, unverified). The break-beam modules claim "100 cm".

---

## 14. Buzzer, LEDs, vibration motor

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (buzzer) | https://www.aliexpress.com/w/wholesale-ws2812-buzzer.html (search page; item ID not captured) | ≈ €1.00 ($1.09) | 1–5 | Active 5 V buzzer (generic) |
| AliExpress (WS2812B ring) | https://www.aliexpress.us/w/wholesale-ws2812b-led-ring.html (search page) | ≈ €1.20 ($1.30) | 1 | "WS2812B 8/16/24/35/45 LED Pixel Ring … 5V DC" |
| AliExpress (single WS2812B) | https://www.aliexpress.us/item/3256805960867221.html | unverified | per lot | "10mm Addressable WS2812B RGB LED Pixel Module 5V" |
| AliExpress (1027 coin motor) | https://www.aliexpress.com/w/wholesale-coin-vibration-motor-1027.html (search page) | ≈ €5.10 per 20 ($5.70) | 20 | "Mini Vibration Motor DC 3V 12000rpm Flat Coin" (10 × 2.7 mm) |
| Amazon.it (WS2812B ring) | https://www.amazon.it/dp/B0B48GPP56 | unverified | 1 | "WS2812B … Ring 8/16/24/35/45Leds … DC5V (8 LEDs)" |

**Not confirmed on Amazon.it:** a 5 V active buzzer or a 1027 coin motor with a price.

---

## 15. M3 heat-set inserts and screws

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.us/item/3256802711669116.html | ≈ €1.00 ($1.09 sale) | 100 | "M3 … Knurled Brass … Heat Set … for 3D Printer Voron 2.4 M3x5x4" |
| AliExpress | https://www.aliexpress.us/item/3256803999444945.html | ≈ €1.20–7.10 ($1.33–7.85 seen; unverified) | 100 | "M3 Brass Heat Set Inserts 4.6mm OD" (M3 × 5.7 × OD 4.6) |
| Amazon.it (ruthex) | https://www.amazon.it/dp/B08BCRZZS3 | **€9.99** | 100 | "RX-M3x5.7" (L 5.7 mm, OD 4.6 mm per ruthex convention) |
| Amazon.it (Whisverse) | https://www.amazon.it/dp/B0BNHZDCMW | unverified | 100 | "M3X5X4, per stampante 3D Voron 2.4" |
| AliExpress (screws) | https://www.aliexpress.us/item/2251832660603421.html | unverified | 250 | "DIN912 M1.6 M2 M2.5 M3 304 Stainless … Assortment" |
| Amazon.it (screws + nuts + washers) | https://www.amazon.it/dp/B0DZHMX6C9 | unverified | 520 | M3–M6 socket head, nuts and washers, M3 up to 20 mm |
| Amazon.it (screw kit) | https://www.amazon.it/dp/B093LLJSNR | €11.99 | 300 | M2.5–M8 stainless hex screws with keys |

**Insert size labels are inconsistent.**
- The common "M3×5.7" insert is OD 4.6 mm, not 4.0.
- "M3×5×4" (Voron) is usually L 4 mm with OD ~5 mm (unverified from listing).
- **An OD 4.0–4.2 mm insert was not found.** Read the size table and design the hole to the OD you buy.
- DIN 912 (cap head) and ISO 7380 (button head) are different heads. Buy the ISO 7380 separately if needed.

---

## 16. Bearings, shaft, collars, dowel pins

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (FUSHI) | https://www.aliexpress.us/item/3256803520974023.html | ≈ €2.85 ($3.17) | 10 | "608ZZ Bearing Steel … 8*22*7mm … 52100 Chrome Steel" |
| Amazon.it (XiKe) | https://www.amazon.it/dp/B07JJ1SKL4 | **€13.99** | 10 | 608ZZ 8 × 22 × 7, chrome steel, ABEC-3, pre-lubricated |
| Amazon.it (YIXISI) | https://www.amazon.it/dp/B09TXQ7PF6 | €6.99 | 10 | ABEC-7 claimed; one review reports an 8.2 mm bore |
| AliExpress (shaft) | https://www.aliexpress.com/i/32355305302.html | ≈ €1.00–1.50 ($1.09–1.64) | 1 | "WCS8mm linear shaft L100mm chrome plated"; GCr15, HRC 60–62, Ra 0.4 |
| Amazon.it (DOLD shaft) | https://www.amazon.it/dp/B07VTS6RFJ | €15.80/m + €0.55/cut (≈ €2.13 for 100 mm, derived) | cut to length | "Albero di precisione 8 mm h6, acciaio inox X46CR13 … temprato" |
| Amazon.it (collars) | https://www.amazon.it/dp/B0B7XFMWM5 | **€6.56** | 5 | 8 mm locking collar, stainless, OD 14 mm |
| AliExpress (dowels 3 mm) | https://www.aliexpress.us/item/2251832702191202.html | ≈ €9.55/lot ($10.60) | 50/200 | "M3 GB119 SUS304 … Dowel Pins … M3*8/10/12/16/20/25/30mm" |
| AliExpress (dowels 2–8 mm) | https://www.aliexpress.us/item/3256809375710581.html | unverified (4 mm, 100 pcs ≈ $10.19 seen) | 100 | "GB119 Stainless Steel Dowel Pins M2 … M8" |
| Amazon.it (hardened, DIN 6325) | https://www.amazon.it/dp/B086D8Z37D | ≈ €7.50 | 10 | "3 x 22 DIN 6325 EN ISO 8734 tolleranza m6 acciaio temprato". **4×20 and 3×16 were not found**; the same seller lists many sizes |

---

## 17. Braided PE (Dyneema) line, 0.4–0.6 mm, ≥ 40 kg

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (DORISEA) | https://www.aliexpress.us/item/2255800276590006.html | ≈ €0.90 ($0.99 shown; likely the shortest or thinnest variant) | 100–2000 m | 8-strand; "0.50mm … 90 lb (≈ 40.8 kg); 0.55mm … 100 lb" |
| AliExpress (JOF X8) | https://www.aliexpress.us/item/3256808854213879.html | unverified ($0.99–5.26 seen) | 150–500 m | "8 Strand … 15 20 30 40 50 60 80 100 [lb]", 0.14–0.50 mm |
| Amazon.it (8-strand 500 m) | https://www.amazon.it/dp/B089CSYTP8 | €18.99 | 500 m | "8.3-40kg"; 0.4 mm = 70 lb (31.8 kg). The 40 kg variant's diameter is unverified |

**Note:** braid ratings vary between brands. A 0.50 mm / 90–100 lb line meets ≥ 40 kg, but knots lose 30–50%, so size up.

---

## 18. M6 eye bolts, threaded rod, wing nuts

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/1005003371084392.html | €6.44 (1), €5.09/pc at 2 or more | 1–5 | "M3 M4 M5 M6 M8 M10 DIN580 Lifting eye … bolts Stainless steel" |
| AliExpress | https://www.aliexpress.com/i/4000274813385.html | unverified | 2 | "M4 M5 M6 M8 304 Stainless Steel Sheep Eye screw Bolt … with 2pieces nuts" |
| Amazon.it (wing nuts) | https://www.amazon.it/dp/B0848V9K61 | **€8.94** | 10 | "Dadi a farfalla M6 in acciaio inox 304" |
| Amazon.it (threaded rod) | https://www.amazon.it/dp/B09PLJ1GPW | €21.07 | 10 × 130 mm | M6 A2/304 threaded rod |
| Amazon.it (threaded rod 1 m) | https://www.amazon.it/dp/B00LOR3OLK | €15.16 | 1 m | **AISI 316 DIN 975 M6, LEFT-HAND thread. Do not buy by mistake** |

**Tip:** a local ferramenta (Milan) is cheaper for an M6 rod (≈ €2–4/m zinc-plated, an unverified estimate).

---

## 19. Wire, connectors, protoboard

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| AliExpress (silicone wire) | https://www.aliexpress.us/item/2251832829997304.html | unverified | kit | "26/24/22/18 AWG Silicone Wire Kit 6 Colors", UL, 300 V, tinned |
| AliExpress (silicone wire) | https://www.aliexpress.us/item/3256805264231583.html | unverified | 5 colours × 10 m | 16–30 AWG, −60 to 200 °C |
| Amazon.it (JST-XH kit, HALJIA) | https://www.amazon.it/dp/B07V1DBQZJ | ≈ €15.99 | kit | JST-XH 2–7 pin with 90 pre-crimped 22 AWG silicone leads |
| Amazon.it (JST-XH pre-crimped, elechawk) | https://www.amazon.it/dp/B0BPQRM664 | ≈ €16.99 | kit | JST-XH 2–10 pin, 22 AWG silicone |
| Amazon.it (proto kit, ALLECIN) | https://www.amazon.it/dp/B0CKZ7GFSK | **€17.99** | 20 boards + headers + 18 terminal blocks | double-sided boards in 6 sizes, including 2 × (5 × 7 cm); 5 mm screw terminals |

**Not captured:** an AliExpress JST-PH or XH crimp kit and a standalone 5 × 7 perfboard listing (prices unverified). Search terms: "JST XH 2.54 kit 230pcs" and "5x7 double side prototype PCB 10pcs".

---

## 20. TPU filament
Skipped (already owned).

---

## Where Amazon.it (or an EU shop) is clearly better value
- **#6 springs:** buy from Gutekunst rather than either marketplace. It is the only source with published R, F0, Fn and Ln, at €6–6.60 per spring plus about €8.55 shipping, falling to about €2.50–2.93 per spring at 3–7 pieces.
- **#11 PSU:** alimentatorishop.it, €14.98 excl. VAT for a genuine Mean Well, beats Amazon.it (no price shown) and unbranded AliExpress bricks.
- **#12 limit switches:** Amazon.it RELAND SUN at €2.37 for 10 is on par with AliExpress, with faster delivery.
- **#16 shaft:** Amazon.it DOLD cut-to-length 8 mm h6 hardened stainless (≈ €2.13 for 100 mm) is good value for precision.
- **Everything else** (ESP32, TP4056, DRV8871, MP1584, inserts, bearings, sensors) costs 3–10× more on Amazon.it than on AliExpress. Only pay that for speed.

---

# Added items (coordinator request), seen 2026-10-25, same method and caveats

## 21. Hydraulic shock absorber, M14 × 1.5, 12–16 mm stroke (and the M12 AC1210 class)

### Published performance data (from catalogue or distributor sources, not the marketplace listing)

| model | thread | stroke | max energy / cycle | max energy / hour | max effective mass | return force | max impact speed | source |
|---|---|---|---|---|---|---|---|---|
| **SMC RB1412** (genuine) | M14×1.5 | 12 mm | **19.6 J** | 45 cycles/min max → ≈ 882 J/min, ≈ 52.9 kJ/h (derived) | not retrieved | **15.98 N max** (Nextevo listing; unverified vs SMC sheet) | 0.05–5 m/s | https://www.smcworld.com/webcatalog/s3s/en-jp/detail/?partNumber=RB1412 , https://www.nextevo.eu/en/rb1412-shock-absorber , https://us.misumi-ec.com/vona2/detail/221006500174/?HissuCode=RB1412 |
| **AC1416-2** (CJAC/EMC-type, generic) | M14×1.5 | 16 mm | **20 J** ("20 Nm") | **not found** | **≈ 32 kg** ("70 lb") | **not found** | 1.5 m/s (-2 = medium speed); the family table gives 2.6 / 1.5 / 0.8 m/s for the -1 / -2 / -3 variants | https://www.nextdayautomation.com/products/used-lot-of-2-cjac-ac1416-2-shock-absorber-16mm-stroke-20-nm-max-70lb-max-m14x1-5 , https://www.hennlich.cz/en/lin-tech/emc-ac1416-2/ |
| AC1412-2 | M14×1.5 | 12 mm | 20 J | not found | not found | not found | same table as AC1416 | (comparison table in the same search; source page not pinned) |
| **AC1210-2** | M12×1.0 | 10 mm | **5 J** (marketplace) or **6 J** (comparison table) | **17,640 J/h** ("17640 Nm/h", marketplace) | 5–30 kg (marketplace, unit garbled) | not found | 0.8–3 m/s (listing) or 1.5 m/s (Hennlich, -2) | https://www.hennlich.cz/en/lin-tech/emc-ac1210-2/ , https://www.amazon.com/dp/B07HG9DHBX |
| Airtac ACA1416-1 / -2 | M14×1.5 | 16 mm | "high", **no number published on the pages found** | — | — | — | -1 high speed/light load; -2 medium speed/medium load | https://www.airtacs.com/products/airtac-aca-accessories-shock-absorber-aca1416-2 |

- **Return force for the AC-series was not found anywhere.** Typical small self-compensating units are about 5–20 N, which is an unverified class estimate.
- **For sizing, use the SMC RB1412.** It is the only M14 unit here with a full datasheet and an EU distribution network (SMC Italia, Misumi EU, RS).
- **Price of the genuine RB1412 was not retrieved.** It is typically tens of euros (unverified).

### Purchase listings

| source | URL | price (EUR) | pack qty | key specs (verbatim) |
|---|---|---|---|---|
| AliExpress | https://www.aliexpress.com/item/32694169348.html | ≈ €8.50 ("9.4US $" in title) | 1 | "AC1416-3 … Low speed AC series OD thread size 14mm stroke 16mm Specifications M14*1.5". **This is the -3 (low-speed) variant; pick -2 for medium speed** |
| AliExpress (multi-model) | https://www.aliexpress.us/item/3256808147360808.html | ≈ €8.30 ($9.21 for the AC1416-02 variant) | 1 | "Pneumatic Cylinder Shock Absorber AC series AC0806 AC1425 AC1008 AC2050 … self-compensation" |
| AliExpress (AD adjustable) | https://www.aliexpress.us/item/3256807553861304.html | unverified ($1.09–12.49 seen; AD1416-5 at $12.49) | 1 | "AD1410 AD1412 AD1416 … Hydraulic Shock Absorber Air Buffer AirTac Type" (AD = adjustable) |
| Amazon.it (AC series selector) | https://www.amazon.it/dp/B0FDX1VBBM | unverified (no price in snippet) | 1 | "Ammortizzatore idraulico … AC1210-2 AC1410-2 AC1412-2 AC1416-2 AC1420-2 …" (variant selector) |
| Amazon.it (AC1420-2 variant) | https://www.amazon.it/dp/B0FB3Y4J66 | €12.99–21.87 (range shown; unverified per variant) | 1 | M14 × 20 mm stroke AC1420-2. Same listing family offers AC1416-2 |
| Amazon.it (AD1412-5 / 1416) | https://www.amazon.it/dp/B07VRDG736 | unverified | 1 | "Oil Pressure Adjustable Shock Absorber with 10/12/16mm Stroke" |
| Amazon.it (AC1210) | https://www.amazon.it/dp/B0DHKZZ1XY | unverified | 1 | "Ammortizzatore idraulico … regolabile … (AC1210)" |

## 22. Cylindrical rubber buffers / anti-vibration mounts, M6

| source | URL | price (EUR) | pack qty | key specs (verbatim / published) |
|---|---|---|---|---|
| **Kipp K0566.02002055** (EU maker; spec via reseller) | https://www.mrosupply.com/hardware/6219475_k056602002055_nk-north-america-inc/ | not retrieved (buy via kipp.com / EU distributors) | 1 | "Type A … 20mm diameter and 20mm height … M6 … 18mm thread length … Shore 55A … **332 N load capacity and 133 N/mm spring stiffness**" |
| Kipp K0566.02001055 | https://www.mrosupply.com/hardware/6219473_k056602001055_nk-north-america-inc/ | not retrieved | 1 | 20 × 10 mm, M6, 55 Shore A: **300 N, 300 N/mm** |
| Kipp K0566.02501555 | https://www.mrosupply.com/hardware/6219478_k056602501555_nk-north-america-inc/ | not retrieved | 1 | 25 × 15 mm, M6×18: **441 N, 294 N/mm** |
| Trygonal Type A datasheet | https://www.trygonal.com/file-download.datasheet-rubber-metal-buffers-type-a.a-2066.pdf | — | — | Load/stiffness table by size and hardness. The 20×20 M6 row exists, but its columns could not be read from the snippet |
| WSW-Power (DE) | https://wsw-power.de/product_info.php?info=p136_gummi-metall-puffer-type-a-20x20-m6.html | **€1.45/pc** | 1 | "Gummi-Metall-Puffer Type A 20x20 M6 beidseitiger Gewindebolzen" (no load data) |
| Normteile Leinigen (DE; Mädler 68930420 cross-ref) | https://www.normteile-leinigen.de/Gummipuffer/GPA0N0202006 | €2.15 incl. VAT (stainless version) | 1 | Form A, D20, M6, L18 |
| Amazon.it (DOJA, male-male) | https://www.amazon.it/dp/B08YN9W4Q3 | **€10.99** | 4 | 20 × 20, M6 male-male; "Max load: 430" kg (implausible; ignore) |
| Amazon.it (DOJA, male-female) | https://www.amazon.it/dp/B08YMZSNJ3 | €11.99 | 4 | 20 × 20 M6; "Maximum load: 220 kg" (seller claim, implausible) |
| Amazon.it (ASFINS) | https://www.amazon.it/dp/B0963L1VW4 | €9.99 | 4 | "25*20, M6*18" (no load data) |
| AliExpress | https://www.aliexpress.us/item/3256809459880950.html | unverified | 4/8 | "Anti-Vibration Rubber Mounts M3-M10 Silentblocks" (no load data) |

**Notes:**
- The Kipp figures are a usable reference for any generic 55 Shore A 20×20 buffer: about 133 N/mm, so roughly 1 mm of deflection at 133 N, with about 332 N max.
- The reseller text says "internal thread" for the K0566, while Type A is normally male/male. Check the Kipp drawing.
- **Amazon and AliExpress load claims are not credible.**

## 23. M8 × 30–40 bolt, 8 × 30 and 4 × 20 dowel pins

| source | URL | price (EUR) | pack qty | key specs |
|---|---|---|---|---|
| Amazon.it (M8×35 socket cap) | https://www.amazon.it/dp/B09TTKDZXW | **€0.35** (single) | 1 | "Vite a testa cilindrica con cava esagonale (M8 x 35 mm)"; grade/material not stated |
| Amazon.it (M8×35 hex, A2) | https://www.amazon.it/dp/B08KP79Y34 | €10.59 | 10 | "AGBERG … M8 x 35 mm … acciaio inox A2 … DIN 933" (fully threaded; poor as a pin) |
| Amazon.it (8×36 hardened dowel) | https://www.amazon.it/dp/B086D7Q6L8 | unverified | 5 | "Cylinder Pins 8 x 36 DIN 6325 EN ISO 8734 Tolerance m6 Hardened Steel" (8×30 not listed; same seller sells 8×20 https://www.amazon.it/dp/B086D5SP1S) |
| Amazon.it (4×30 DIN 7) | https://www.amazon.it/dp/B07DGSBBQP | unverified | 20 | "Cylindrical Pin 3 to 8 mm Din 7 Steel … Tolerance m6 … 4 x 30" (variant selector; check for 4×20) |
| AliExpress (4 mm HRC63) | https://www.aliexpress.com/item/1005003780227334.html | ≈ €0.90/lot ($0.99) | lot | "4mm 5mm OD 20mm … 40mm Length HRC63 Steel Cylinder Needle Locating Roller Dowel Parallel Pin" (4×20 availability unverified) |
| AliExpress (GB119 304 stainless, M2–M8) | https://www.aliexpress.com/item/1005009562025333.html | ≈ €0.75–1.00 ($0.83–1.09 seen) | 5/10/20 | "GB119 Stainless Steel Dowel Pins M2 M2.5 M3 M4 M5 M6 M8"; lengths 8–50 mm (8×30 availability per variant unverified) |

**Recommendation:** for a load-bearing 8 mm pivot, a hardened DIN 6325 / ISO 8734 pin (m6) beats an M8 bolt, since a bolt's threads bear on the hole. If you use a bolt, use a partially threaded DIN 931 or a shoulder bolt. The exact 8×30 and 4×20 sizes were **not** confirmed on Amazon.it or AliExpress. The DIN 6325 seller above has many sizes. An industrial supplier (Misumi EU, Ganter, Bossard) or a local ferramenta will have them.
