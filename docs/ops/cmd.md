cd backend
source venv/bin/activate
uvicorn main:app --reload

cd dash
npm run dev

# MANDATORY ANALYSIS REQUIREMENTS (DO NOT SKIP)

These requirements are additive and must be integrated into existing sections. Do not create duplicate sections.

==================================================
DOCUMENTATION INTERPRETATION REQUIREMENT
========================================

For every indicator below:

- Explain definition
- Explain calculation logic
- Explain current reading
- Explain bullish interpretation
- Explain bearish interpretation
- Explain institutional interpretation
- Explain limitations

Mandatory Indicators:

1. Open
2. High
3. Low
4. Close
5. Volume
6. EMA20
7. EMA50
8. EMA100
9. EMA200
10. RSI
11. OBV
12. CMF
13. VWAP
14. FVG
15. RVOL
16. RVOL_Deviation

==================================================
ADVANCED VOLUME ANALYSIS REQUIREMENT
====================================

In the Advanced Volume Analysis section, the model must explicitly evaluate:

### Vector-Based Volume Analysis

Calculate and interpret:

OBV_Slope = OBV(Current) - OBV(Previous)

Classify:

- Positive Momentum
- Negative Momentum
- Neutral Momentum

Check:

- Consecutive Positive Slopes
- Consecutive Negative Slopes
- Trend Acceleration
- Trend Deceleration

Determine:

- Confirmed Trend
- Weak Trend
- Failed Trend

---

### Relative Volume Validation

Analyze:

- RVOL
- RVOL_Deviation

Classification:

RVOL > 1
= Above Normal Participation

RVOL > 2
= Institutional Participation Alert

RVOL_Deviation > 50%
= Volume Anomaly

Output:

Volume Validation Status

---

### Strategy Logic Validation

Condition 1:

Momentum Confirmation

OBV_Slope > 0

Condition 2:

Volume Validation

RVOL_Deviation > 50%

Determine:

- Full Confirmation
- Partial Confirmation
- No Confirmation

==================================================
INSTITUTIONAL POWER INDEX (IPI) REQUIREMENT
===========================================

Mandatory Formula Review:

Norm_OBV_Slope

CMF Contribution

RVOL Contribution

IPI Score

Formula:

IPI =
(CMF × 100)

- (RVOL_Deviation × 0.5)
- (Norm_OBV_Slope × 50)

Mandatory Output:

- IPI Score Interpretation
- Dominant Component
- Institutional Pressure Direction
- Classification Change Risk

Classification Rules:

IPI > 50
= Institutional Accumulation

-20 ≤ IPI ≤ 50
= Neutral

IPI < -20
= Institutional Distribution

Must explain why classification occurred.

==================================================
INSTITUTIONAL FLOW INDEX (IFI) REQUIREMENT
==========================================

Mandatory Formula Review:

Raw_Flow =
((Close - Open) / Close)
× Volume

Analyze:

- Raw Flow Direction
- Raw Flow Strength

---

IFI Score

Analyze:

- EMA(14) Smoothing Effect
- Trend Persistence
- Trend Reversal Risk

---

Classification Logic

Determine:

- Smart Money Zone
- Retail Distribution Zone
- Neutral Zone

Must explain:

Why the asset belongs in that zone.

==================================================
UIPT REQUIREMENT
================

Mandatory Evaluation Sequence:

Step 1

Historical Accumulation Scan

Look Back:

3–5 prior bars

Check:

Institutional Accumulation Events

---

Step 2

Ignition Detection

Requirements:

RVOL > 2.0

AND

IPI = Accumulation

Output:

Ignition Confirmed?
Yes / No

---

Step 3

Consolidation Detection

Requirements:

CMF > 0

Price Pullback or Sideways

Output:

Healthy Consolidation?
Yes / No

---

Step 4

Pivot Trigger Detection

Requirements:

RVOL > 1.0

Price Stabilization

Output:

Trigger Active?
Yes / No

---

Step 5

Buying Setup Checklist

Evaluate:

- Prior Accumulation
- Positive CMF
- RVOL Recovery
- Price Stabilization
- Institutional Footprint

Output:

PASS / FAIL

for every condition.

---

Step 6

Professional Advice Logic

Mandatory Rule:

If CMF < 0

Then:

Flag Institutional Exit Risk

Reduce Watchlist Priority

Must explicitly state this.

==================================================
EXTENDED SESSION ANALYSIS REQUIREMENT
=====================================

If Extended Session data exists:

Calculate:

ExtVolumeRatio

Formula:

ExtendedVolume /
AverageDailyVolume

---

Noise Filter

If ExtVolumeRatio < 5%

Ignore Signal

Classify:

Low Reliability

---

Significant Event Detection

If ExtVolumeRatio > 15%

Classify:

Significant Institutional Event

Possible Causes:

- Earnings
- Guidance
- Analyst Upgrade
- Institutional Activity

---

Gap Quality Analysis

Evaluate:

Gap Size

Gap Direction

Gap Reliability

Mandatory Rule:

Gap with High Extended Volume

>

Gap with Low Extended Volume

---

Extended Score

ExtendedPriceChange(%)
×
min(ExtVolumeRatio,0.30)

Interpret result.

==================================================
LATEST FINANCIAL NEWS REQUIREMENT
=================================

Analyze EVERY news article supplied.

For EACH article provide:

- Headline
- Summary
- Affected Markets
- Affected Sectors
- Affected ETFs
- Affected Commodities
- Affected Bonds
- Affected Currency Markets
- Affected Crypto Markets

Evaluate:

- Risk-On Impact
- Risk-Off Impact

Then determine:

Impact on:

- Market Regime
- Liquidity
- Inflation
- Growth Expectations
- Institutional Positioning

==================================================
CORE RADAR INTEGRATION REQUIREMENT
==================================

Every major conclusion must be mapped into:

1. THE REGIME SHIFT
2. SECTOR & LEADER RADAR
3. TECHNICAL CONFLUENCE
4. ACTIONABLE RADAR
5. HIDDEN RISK

No conclusion may exist outside the Core Radar framework.

==================================================
FINAL OUTPUT REQUIREMENT
========================

Always finish with:

Core Radar Dashboard

Followed by:

Core Radar Summary:
[Risk-On / Risk-Off / Reflation / Stagflation]

Top Watchlist:
[X, Y, Z]
