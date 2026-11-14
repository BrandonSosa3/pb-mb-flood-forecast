# Rain near high tide, 2000–2026 (rule check)

_Written by `pipeline/rain_history.py` on 2026-11-14._

Rule: ≥ 0.25 in of rain at San Diego airport within 3 h of the day's highest
tide, with the water at La Jolla ≥ 6.0 ft MLLW (Mission Beach then has 100+ properties on ground
below the water). La Jolla stands in for Mission Bay (similar levels).

- Days with ≥ 0.25 in near the high tide: **94** in 28 years (~3.4 a year)
- Of those, high tide ≥ 6.0 ft (rule fires): **32** (~1.1 a year)

## Days the rule would have fired
| Day | High tide | Water (ft) | Rain near tide (in) | Rain that day (in) |
|---|---|---|---|---|
| Fri Oct 27, 2000 | 9 AM | 6.1 | 0.31 | 0.31 |
| Thu Jan 11, 2001 | 10 AM | 7.07 | 0.47 | 1.08 |
| Fri Jan 12, 2001 | 10 AM | 6.28 | 0.61 | 0.82 |
| Fri Dec 20, 2002 | 8 AM | 6.34 | 0.43 | 0.43 |
| Wed Oct 27, 2004 | 9 AM | 6.82 | 0.72 | 2.71 |
| Thu Oct 28, 2004 | 9 AM | 6.54 | 0.43 | 0.45 |
| Tue Dec 28, 2004 | 9 AM | 6.29 | 0.89 | 1.27 |
| Fri Feb 11, 2005 | 10 AM | 6.06 | 0.46 | 1.2 |
| Mon Feb 21, 2005 | 7 AM | 6.15 | 1.28 | 2.18 |
| Wed Feb 23, 2005 | 8 AM | 6.21 | 0.29 | 0.47 |
| Mon Oct 17, 2005 | 9 AM | 6.47 | 0.25 | 0.38 |
| Thu Nov 27, 2008 | 8 AM | 6.31 | 1.22 | 1.26 |
| Mon Dec 15, 2008 | 10 AM | 6.5 | 0.41 | 0.88 |
| Mon Feb 09, 2009 | 9 AM | 6.91 | 0.3 | 0.37 |
| Sat Feb 27, 2010 | 8 AM | 6.83 | 0.33 | 0.71 |
| Tue Dec 21, 2010 | 8 AM | 6.76 | 1.34 | 2.01 |
| Wed Dec 22, 2010 | 9 AM | 7.1 | 0.56 | 1.83 |
| Sun Mar 20, 2011 | 10 PM | 6.48 | 0.81 | 0.67 |
| Mon Dec 12, 2011 | 9 AM | 6.23 | 0.39 | 0.5 |
| Thu Dec 13, 2012 | 8 AM | 7.57 | 1.44 | 1.56 |
| Sat Mar 01, 2014 | 9 AM | 6.0 | 0.5 | 1.01 |
| Thu Jan 07, 2016 | 6 AM | 6.44 | 0.44 | 0.55 |
| Fri Dec 16, 2016 | 10 AM | 6.53 | 0.47 | 1.26 |
| Mon Feb 04, 2019 | 8 AM | 6.06 | 0.38 | 0.97 |
| Thu Nov 28, 2019 | 9 AM | 6.98 | 0.59 | 1.37 |
| Mon Dec 23, 2019 | 6 AM | 6.73 | 0.89 | 1.34 |
| Thu Dec 26, 2019 | 8 AM | 6.96 | 0.6 | 1.28 |
| Thu Apr 09, 2020 | 11 PM | 6.27 | 1.04 | 0.83 |
| Tue Mar 21, 2023 | 10 AM | 6.2 | 0.56 | 1.06 |
| Mon Jan 22, 2024 | 7 AM | 6.3 | 2.35 | 2.73 |
| Tue Feb 06, 2024 | 5 AM | 6.2 | 0.32 | 0.89 |
| Thu Jan 01, 2026 | 7 AM | 6.92 | 1.9 | 2.08 |

## Wettest high tides below the level (rule does not fire)
| Day | Water (ft) | Rain near tide (in) |
|---|---|---|
| Thu May 14, 2015 | 5.83 | 1.59 |
| Tue Sep 15, 2015 | 5.68 | 1.15 |
| Tue Feb 25, 2003 | 5.64 | 0.96 |
| Mon Dec 07, 2009 | 5.44 | 0.9 |
| Wed Mar 15, 2023 | 4.58 | 0.82 |
| Sat Feb 26, 2011 | 4.98 | 0.76 |
| Wed Dec 04, 2019 | 4.54 | 0.71 |
| Mon Feb 27, 2017 | 5.72 | 0.7 |
