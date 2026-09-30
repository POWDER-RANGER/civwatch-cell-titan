<!-- ══════════════════════════════════════════ CELL TITAN HEADER -->
<div align="center">

[![Header](https://capsule-render.vercel.app/api?type=waving&color=0:0D1117,35:0D2818,70:1B5E20,100:00E5FF&height=300&section=header&text=CELL+TITAN&fontSize=70&fontColor=00E5FF&animation=fadeIn&fontAlignY=42&desc=Defensive+RF+Observability+Platform+%E2%80%94+In+Development&descColor=80DEEA&descSize=18&descAlignY=64)](https://github.com/POWDER-RANGER/civwatch-cell-titan)

<br>

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Share+Tech+Mono&weight=700&size=18&duration=2600&pause=700&color=00E5FF&center=true&vCenter=true&width=900&lines=Cellular+%E2%80%94+Wi-Fi+%E2%80%94+D2D+%E2%80%94+Transport;ADB+Live+Telemetry+%E2%80%94+Cryptographic+Evidence+Chain;Multi-domain+Defensive+RF+Intelligence+System)](https://github.com/POWDER-RANGER/civwatch-cell-titan)

<br>

![](https://img.shields.io/badge/RF_PLATFORM-IN_DEV-FF9100?style=for-the-badge&labelColor=0D1117)
![](https://img.shields.io/badge/DOMAINS-4_PLANNED-00E5FF?style=for-the-badge&labelColor=0D1117)
![](https://img.shields.io/badge/USE-DEFENSIVE_ONLY-00C853?style=for-the-badge&labelColor=0D1117)

</div>

---

## 📡 What Is CELL TITAN?

**CIVWATCH CELL TITAN** is a defensive RF intelligence system in development. It is designed to turn Android devices into federated sensors for real-time radio frequency monitoring across multiple domains.

> **Status: in development.** This repository currently contains the launch scaffolding (launch scripts, config, requirements). Core telemetry, correlation, and evidence-chain modules are being built and will merge into the unified CIVINTELLIGENCE platform.

## ✨ Planned Features

| Feature | Description | Status |
|---------|-------------|--------|
| 📱 **ADB Live Telemetry** | Live cellular + Wi-Fi data via Android Debug Bridge | 🟡 In development |
| 🌐 **Multi-Domain Coverage** | Cellular, Wi-Fi, D2D (Device-to-Device), Transport | 🟡 Scaffolding |
| 🔐 **Cryptographic Evidence Chain** | Tamper-evidence collection with chain of custody | 🟡 Designed |
| 🔗 **Cross-Domain Correlator** | Correlate signals across RF domains for pattern detection | 🔴 Planned |
| 🖥️ **Cyberpunk Dashboard** | Live topology visualization | 🟡 In development |
| 💾 **Event-Sourced Storage** | Complete audit trail of all RF events | 🔴 Planned |
| 🌐 **Federated Sensors** | Deploy multiple Android sensors across a geographic area | 🔴 Planned |

## 🚀 Launch

```bash
# Launch the RF observability platform
./launch.sh

# Dashboard available at http://localhost:8000
# Enable USB debugging on your Android device and connect via ADB
```

## 🏗️ System Architecture

```
╔═══════════════════════════════════════════════════════════════════════════╗
║                    CELL TITAN — RF OBSERVABILITY PLATFORM                ║
║                                                                          ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │                    FEDERATED SENSORS                              │   ║
║  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   ║
║  │  │Android 1│  │Android 2│  │Android 3│  │Android N│  ...       │   ║
║  │  │  ADB    │  │  ADB    │  │  ADB    │  │  ADB    │            │   ║
║  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘            │   ║
║  └───────┼────────────┼────────────┼────────────┼───────────────────┘   ║
║          └─────────────────┴────────┬────────┴─────────────────┘          ║
║                                    ▼                                      ║
║                    ┌───────────────────────────────┐                     ║
║                    │    INGESTION PIPELINE          │                     ║
║                    │  Cellular │ Wi-Fi │ D2D │ Transport               │  ║
║                    └───────────────┬───────────────┘                     ║
║                                    ▼                                      ║
║                    ┌───────────────────────────────┐                     ║
║                    │    CROSS-DOMAIN CORRELATOR     │                     ║
║                    │  Pattern detection │ Anomaly   │                     ║
║                    └───────────────┬───────────────┘                     ║
║                                    ▼                                      ║
║                    ┌───────────────────────────────┐                     ║
║                    │   CRYPTOGRAPHIC EVIDENCE CHAIN │                     ║
║                    │  SHA-256 chain │ Timestamping  │                     ║
║                    └───────────────┬───────────────┘                     ║
║                                    ▼                                      ║
║                    ┌───────────────────────────────┐                     ║
║                    │      CYBERPUNK DASHBOARD       │                     ║
║                    │  Live topology │ Signal flows  │                     ║
║                    └───────────────────────────────┘                     ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

## 📡 RF Domains

| Domain | Protocols | Status |
|--------|-----------|--------|
| **Cellular** | LTE, 5G NR, GSM, CDMA | 🟡 Scaffolding |
| **Wi-Fi** | 802.11a/b/g/n/ac/ax | 🟡 Scaffolding |
| **D2D (Device-to-Device)** | LTE-D2D, NR Sidelink | 🔴 Planned |
| **Transport** | Bluetooth, BLE, NFC | 🔴 Planned |

---

## 🔔 Consolidation Notice

CELL TITAN is being consolidated into the unified CIVINTELLIGENCE platform. See the
[consolidation charter and plan (Phase 3: merge as the defensive sensing module)](https://github.com/POWDER-RANGER/CivilianIntelligence/blob/main/docs/CIVINTELLIGENCE.md).

## 🤝 Connect

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Curtis_Farrar-0077B5?style=flat&logo=linkedin)](https://www.linkedin.com/in/curtis-farrar-g6b)
[![GitHub](https://img.shields.io/badge/GitHub-POWDER--RANGER-181717?style=flat&logo=github)](https://github.com/POWDER-RANGER)
[![Portfolio](https://img.shields.io/badge/Portfolio-powder--ranger.github.io-00E5FF?style=flat&logo=githubpages)](https://powder-ranger.github.io)
[![ORCID](https://img.shields.io/badge/ORCID-0009--0008--9273--2458-A6CE39?style=flat&logo=orcid)](https://orcid.org/0009-0008-9273-2458)

---

**RF Intelligence. Real-Time. Defensive Only.**

<div align="center">

[![Footer](https://capsule-render.vercel.app/api?type=waving&color=0:00E5FF,35:006064,70:001A25,100:0D1117&height=150&section=footer)](https://github.com/POWDER-RANGER/civwatch-cell-titan)

</div>
