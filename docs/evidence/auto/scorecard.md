# Automatic scorecard

_Rewritten by `pipeline/auto_verify.py` on 2026-11-27 10:17 UTC. Do not edit by hand._

Every saved forecast is compared with what happened, using evidence collected automatically: measured rain and water level, City Get It Done flood reports, NWS storm reports and local news. Rules are in the script.

**8 right · 13 close · 0 missed · 0 false alarms**, plus 20 coast days not scored (no reports either way). 4 rain scores rest on zero City reports (weak evidence).

| Day | What | We said | Observed | Result | Evidence |
|---|---|---|---|---|---|
| 2026-11-26 | Coast: Pacific Beach | Moderate | No reports | unverified (prelim.) | Mission Bay peaked at 8.1 ft. No flooding reported from Pacific Beach to the City, NWS or local news. |
| 2026-11-26 | Coast: Mission Beach | Major | Moderate | close (prelim.) | Mission Bay peaked at 8.1 ft. 0 City flood reports in Mission Beach on a high-tide day, 1 NWS storm report. |
| 2026-11-26 | Coast: Crown Point | Minor | No reports | unverified (prelim.) | Mission Bay peaked at 8.1 ft. No flooding reported from Crown Point to the City, NWS or local news. |
| 2026-11-25 | Coast: Pacific Beach | Moderate | Minor | close (prelim.) | Mission Bay peaked at 8.3 ft. 1 City flood report in Pacific Beach on a high-tide day, 3 news storys. |
| 2026-11-25 | Coast: Mission Beach | Moderate | Minor | close (prelim.) | Mission Bay peaked at 8.3 ft. 2 City flood reports in Mission Beach on a high-tide day, 3 news storys. |
| 2026-11-25 | Coast: Crown Point | Minor | Minor | right (prelim.) | Mission Bay peaked at 8.3 ft. 0 City flood reports in Crown Point on a high-tide day, 3 news storys. |
| 2026-11-24 | Coast: Pacific Beach | Moderate | Minor | close | Mission Bay peaked at 8.2 ft. 1 City flood report in Pacific Beach on a high-tide day, 3 news storys. |
| 2026-11-24 | Coast: Mission Beach | Moderate | Moderate | right | Mission Bay peaked at 8.2 ft. 2 City flood reports in Mission Beach on a high-tide day, 1 NWS storm report, 5 news storys. |
| 2026-11-24 | Coast: Crown Point | Minor | Minor | right | Mission Bay peaked at 8.2 ft. 0 City flood reports in Crown Point on a high-tide day, 3 news storys. |
| 2026-11-23 | Coast: Pacific Beach | Moderate | Minor | close | Mission Bay peaked at 8.0 ft. 1 City flood report in Pacific Beach on a high-tide day. |
| 2026-11-23 | Coast: Mission Beach | Moderate | Minor | close | Mission Bay peaked at 8.0 ft. 0 City flood reports in Mission Beach on a high-tide day, 2 news storys. |
| 2026-11-23 | Coast: Crown Point | Minor | No reports | unverified | Mission Bay peaked at 8.0 ft. No flooding reported from Crown Point to the City, NWS or local news. |
| 2026-11-22 | Coast: Pacific Beach | Minor | Minor | right | Mission Bay peaked at 7.6 ft. 1 City flood report in Pacific Beach on a high-tide day, 1 news story. |
| 2026-11-22 | Coast: Mission Beach | Minor | No reports | unverified | Mission Bay peaked at 7.6 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-22 | Coast: Crown Point | Low | Minor | close | Mission Bay peaked at 7.6 ft. 0 City flood reports in Crown Point on a high-tide day, 1 news story. |
| 2026-11-21 | Coast: Pacific Beach | Low | Minor | close | Mission Bay peaked at 7.0 ft. 0 City flood reports in Pacific Beach on a high-tide day, 1 news story. |
| 2026-11-21 | Coast: Mission Beach | Minor | No reports | unverified | Mission Bay peaked at 7.0 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-21 | Coast: Crown Point | Low | Minor | close | Mission Bay peaked at 7.0 ft. 0 City flood reports in Crown Point on a high-tide day, 1 news story. |
| 2026-11-20 | Coast: Mission Beach | Minor | No reports | unverified | Mission Bay peaked at 6.6 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-19 | Rain: Pacific Beach | Low | Low | right | 0.40 in of rain at San Diego airport (heaviest 6 hours 0.40 in). No flood reports from Pacific Beach to the City, NWS or local news. |
| 2026-11-19 | Rain: Mission Beach | Low | Minor | close | 0.40 in of rain at San Diego airport (heaviest 6 hours 0.40 in). 0 City flood reports in Mission Beach, 1 news story. |
| 2026-11-19 | Rain: La Jolla | Low | Low | right | 0.40 in of rain at San Diego airport (heaviest 6 hours 0.40 in). No flood reports from La Jolla to the City, NWS or local news. |
| 2026-11-19 | Coast: Mission Beach | Low | Minor | close | Mission Bay peaked at 6.1 ft. 0 City flood reports in Mission Beach on a high-tide day, 1 news story. |
| 2026-11-18 | Coast: Pacific Beach | Low | No reports | unverified | Mission Bay peaked at 5.5 ft. No flooding reported from Pacific Beach to the City, NWS or local news. |
| 2026-11-18 | Coast: Mission Beach | Low | Minor | close | Mission Bay peaked at 5.5 ft. 0 City flood reports in Mission Beach on a high-tide day, 1 news story. |
| 2026-11-18 | Coast: Crown Point | Low | No reports | unverified | Mission Bay peaked at 5.5 ft. No flooding reported from Crown Point to the City, NWS or local news. |
| 2026-11-17 | Coast: Pacific Beach | Low | No reports | unverified | Mission Bay peaked at 5.3 ft. No flooding reported from Pacific Beach to the City, NWS or local news. |
| 2026-11-17 | Coast: Mission Beach | Minor | No reports | unverified | Mission Bay peaked at 5.3 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-17 | Coast: Crown Point | Low | No reports | unverified | Mission Bay peaked at 5.3 ft. No flooding reported from Crown Point to the City, NWS or local news. |
| 2026-11-16 | Rain: Pacific Beach | Low | Minor | close | 0.25 in of rain at San Diego airport (heaviest 6 hours 0.23 in). 2 City flood reports in Pacific Beach. |
| 2026-11-16 | Rain: Mission Beach | Low | Low | right | 0.25 in of rain at San Diego airport (heaviest 6 hours 0.23 in). No flood reports from Mission Beach to the City, NWS or local news. |
| 2026-11-16 | Rain: La Jolla | Low | Low | right | 0.25 in of rain at San Diego airport (heaviest 6 hours 0.23 in). No flood reports from La Jolla to the City, NWS or local news. |
| 2026-11-16 | Coast: Pacific Beach | Low | No reports | unverified | Mission Bay peaked at 5.4 ft. No flooding reported from Pacific Beach to the City, NWS or local news. |
| 2026-11-16 | Coast: Mission Beach | Low | No reports | unverified | Mission Bay peaked at 5.4 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-16 | Coast: Crown Point | Low | No reports | unverified | Mission Bay peaked at 5.4 ft. No flooding reported from Crown Point to the City, NWS or local news. |
| 2026-11-15 | Coast: Pacific Beach | Low | No reports | unverified | Mission Bay peaked at 5.9 ft. No flooding reported from Pacific Beach to the City, NWS or local news. |
| 2026-11-15 | Coast: Mission Beach | Minor | No reports | unverified | Mission Bay peaked at 5.9 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-15 | Coast: Crown Point | Low | No reports | unverified | Mission Bay peaked at 5.9 ft. No flooding reported from Crown Point to the City, NWS or local news. |
| 2026-11-14 | Coast: Pacific Beach | Minor | No reports | unverified | Mission Bay peaked at 6.5 ft. No flooding reported from Pacific Beach to the City, NWS or local news. |
| 2026-11-14 | Coast: Mission Beach | Minor | No reports | unverified | Mission Bay peaked at 6.5 ft. No flooding reported from Mission Beach to the City, NWS or local news. |
| 2026-11-14 | Coast: Crown Point | Low | No reports | unverified | Mission Bay peaked at 6.5 ft. No flooding reported from Crown Point to the City, NWS or local news. |
