"""A/B test analysis: did the ad increase conversion compared with a PSA (control)?

Run from the ab-test-marketing folder:  python analysis.py
Prints every number used in the README and saves charts + tables to outputs/.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import (
    confint_proportions_2indep,
    proportion_confint,
    proportion_effectsize,
    proportions_ztest,
)

HERE = Path(__file__).parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "axes.edgecolor": GRID, "axes.labelcolor": MUTED, "xtick.color": MUTED,
    "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "figure.dpi": 150,
})

df = pd.read_csv(HERE / "data" / "marketing_AB.csv").drop(columns="Unnamed: 0")
df.columns = ["user_id", "group", "converted", "total_ads", "peak_day", "peak_hour"]
df["converted"] = df["converted"].astype(int)
ad, psa = df[df.group == "ad"], df[df.group == "psa"]

print("=== 1. Data and design checks ===")
print("rows:", len(df), "| duplicate users:", df.user_id.duplicated().sum(), "| missing:", int(df.isna().sum().sum()))
print(df.group.value_counts().to_string())
print("share in control (psa): %.2f%%" % (100 * len(psa) / len(df)))
# The planned split is not documented, so a sample-ratio test cannot be run: the 96/4 split is simply reported.

print("\n=== 2. Are the groups comparable? (randomization check) ===")
print("total ads: ad mean %.1f median %.0f | psa mean %.1f median %.0f"
      % (ad.total_ads.mean(), ad.total_ads.median(), psa.total_ads.mean(), psa.total_ads.median()))
mw = stats.mannwhitneyu(ad.total_ads, psa.total_ads)
# Rank-biserial correlation: 0 = identical, 1 = completely separated.
rbc = 2 * mw.statistic / (len(ad) * len(psa)) - 1
print("Mann-Whitney on total ads: p = %.3g | rank-biserial effect size = %.3f" % (mw.pvalue, rbc))


def cramers_v(ct):
    chi2_, p_, _, _ = stats.chi2_contingency(ct)
    return p_, np.sqrt(chi2_ / (ct.values.sum() * (min(ct.shape) - 1)))


day_ct = pd.crosstab(df.group, df.peak_day)
p_day, v_day = cramers_v(day_ct)
print("peak day vs group: p = %.3g | Cramer's V = %.3f" % (p_day, v_day))
hour_ct = pd.crosstab(df.group, df.peak_hour)
p_hour, v_hour = cramers_v(hour_ct)
print("peak hour vs group: p = %.3g | Cramer's V = %.3f" % (p_hour, v_hour))
print("share of users by peak day (%):")
print((100 * pd.crosstab(df.peak_day, df.group, normalize="columns")).round(1).to_string())
print("share of users by peak hour (%), hours with the biggest gaps:")
hs = 100 * pd.crosstab(df.peak_hour, df.group, normalize="columns")
hs["gap"] = (hs["ad"] - hs["psa"]).abs()
print(hs.sort_values("gap", ascending=False).head(6).round(2).to_string())
# Does the imbalance matter? Compare conversion by day/hour within the control group only.
for col in ["peak_day", "peak_hour"]:
    r = psa.groupby(col).converted.mean() * 100
    print(f"control conversion by {col}: min {r.min():.2f}% max {r.max():.2f}%")

print("\n=== 3. Main result: conversion rate ===")
n_ad, n_psa = len(ad), len(psa)
x_ad, x_psa = ad.converted.sum(), psa.converted.sum()
p_ad, p_psa = x_ad / n_ad, x_psa / n_psa
print(f"ad : {x_ad:,} / {n_ad:,} = {100 * p_ad:.3f}%")
print(f"psa: {x_psa:,} / {n_psa:,} = {100 * p_psa:.3f}%")
diff = p_ad - p_psa
print(f"absolute difference: {100 * diff:.3f} percentage points | relative lift: {100 * diff / p_psa:.1f}%")

z, p_z = proportions_ztest([x_ad, x_psa], [n_ad, n_psa], alternative="two-sided")
chi2, p_chi, _, _ = stats.chi2_contingency(pd.crosstab(df.group, df.converted), correction=False)
print(f"two-proportion z-test: z = {z:.2f}, p = {p_z:.2e}")
print(f"chi-square test:       chi2 = {chi2:.2f}, p = {p_chi:.2e}")

lo, hi = confint_proportions_2indep(x_ad, n_ad, x_psa, n_psa, method="wald", compare="diff")
print(f"95% CI for the difference: {100 * lo:.3f} to {100 * hi:.3f} percentage points")
rlo, rhi = confint_proportions_2indep(x_ad, n_ad, x_psa, n_psa, method="log", compare="ratio")
print(f"95% CI for the relative lift (ratio - 1): {100 * (rlo - 1):.1f}% to {100 * (rhi - 1):.1f}%")
ci_ad = proportion_confint(x_ad, n_ad, method="wilson")
ci_psa = proportion_confint(x_psa, n_psa, method="wilson")
print(f"95% Wilson CI ad : {100 * ci_ad[0]:.3f}% to {100 * ci_ad[1]:.3f}%")
print(f"95% Wilson CI psa: {100 * ci_psa[0]:.3f}% to {100 * ci_psa[1]:.3f}%")

# Bootstrap check on the difference (does not rely on the normal approximation).
rng = np.random.default_rng(42)
boots = (rng.binomial(n_ad, p_ad, 20000) / n_ad) - (rng.binomial(n_psa, p_psa, 20000) / n_psa)
print("bootstrap 95%% CI for the difference: %.3f to %.3f percentage points"
      % (100 * np.percentile(boots, 2.5), 100 * np.percentile(boots, 97.5)))

print("\n=== 3b. Robustness: adjust for the day/hour imbalance (logistic regression) ===")
import statsmodels.formula.api as smf

df["is_ad"] = (df.group == "ad").astype(int)
m0 = smf.logit("converted ~ is_ad", data=df).fit(disp=0)
m1 = smf.logit("converted ~ is_ad + C(peak_day) + C(peak_hour)", data=df).fit(disp=0)
for name, m in [("unadjusted", m0), ("adjusted for day + hour", m1)]:
    orr = np.exp(m.params["is_ad"])
    olo, ohi = np.exp(m.conf_int().loc["is_ad"])
    # average marginal effect of the ad, in percentage points
    d1, d0 = df.copy(), df.copy()
    d1["is_ad"], d0["is_ad"] = 1, 0
    ame = (m.predict(d1) - m.predict(d0)).mean() * 100
    print(f"{name:25s} odds ratio {orr:.2f} (95% CI {olo:.2f} to {ohi:.2f}), p = {m.pvalues['is_ad']:.2e}, "
          f"average effect {ame:.2f} percentage points")

print("\n=== 4. Was the test big enough? (power) ===")
es = proportion_effectsize(p_ad, p_psa)
power_obs = NormalIndPower().power(es, nobs1=n_psa, ratio=n_ad / n_psa, alpha=0.05)
print(f"power to detect the observed effect with these group sizes: {power_obs:.2f}")
# Smallest lift the control group's size could reliably detect (80% power).
mde_es = NormalIndPower().solve_power(nobs1=n_psa, ratio=n_ad / n_psa, alpha=0.05, power=0.8)
# convert Cohen's h back to a rate: p2 = sin^2(asin(sqrt(p1)) + h/2)
p_mde = np.sin(np.arcsin(np.sqrt(p_psa)) + mde_es / 2) ** 2
print(f"minimum detectable conversion at 80% power: {100 * p_mde:.3f}% (lift {100 * (p_mde - p_psa) / p_psa:.0f}% vs {100 * p_psa:.3f}%)")
# Sample size per arm for a 50/50 split to detect the observed lift.
n_needed = NormalIndPower().solve_power(effect_size=es, alpha=0.05, power=0.8, ratio=1.0)
print(f"per-arm size for 80% power at the observed lift with a 50/50 split: {n_needed:,.0f}")

print("\n=== 5. Does exposure matter? (ad group, descriptive only) ===")
bins = [0, 1, 5, 10, 25, 50, 100, 5000]
labels = ["1", "2-5", "6-10", "11-25", "26-50", "51-100", "100+"]
df["ads_bucket"] = pd.cut(df.total_ads, bins=bins, labels=labels)
dose = df.groupby(["group", "ads_bucket"], observed=True).converted.agg(["mean", "count"]).reset_index()
dose["mean"] = (100 * dose["mean"]).round(2)
print(dose.pivot(index="ads_bucket", columns="group", values=["mean", "count"]).to_string())
dose.to_csv(OUT / "conversion_by_ads_bucket.csv", index=False)

# Total ads is measured after assignment, so this split is descriptive, not causal.
for label, mask in [("saw 25 ads or fewer", df.total_ads <= 25), ("saw more than 25 ads", df.total_ads > 25)]:
    a, c = df[mask & (df.group == "ad")], df[mask & (df.group == "psa")]
    zz, pp = proportions_ztest([a.converted.sum(), c.converted.sum()], [len(a), len(c)])
    print(f"{label:22s} ad {100 * a.converted.mean():.2f}% (n={len(a):,}) vs psa {100 * c.converted.mean():.2f}% "
          f"(n={len(c):,}) | diff {100 * (a.converted.mean() - c.converted.mean()):.2f} pp, p = {pp:.3g}")
print("share of ad-group conversions from users who saw more than 25 ads: %.1f%%"
      % (100 * ad[ad.total_ads > 25].converted.sum() / ad.converted.sum()))

print("\n=== 6. Subgroups: day and hour (exploratory; hours with under 100 control users skipped) ===")
rows = []
for col in ["peak_day", "peak_hour"]:
    for val, g in df.groupby(col):
        a, c = g[g.group == "ad"], g[g.group == "psa"]
        if len(c) < 100:
            continue
        zz, pp = proportions_ztest([a.converted.sum(), c.converted.sum()], [len(a), len(c)])
        rows.append((col, val, len(a), len(c), 100 * a.converted.mean(), 100 * c.converted.mean(), pp))
sub = pd.DataFrame(rows, columns=["dimension", "value", "n_ad", "n_psa", "ad_rate_pct", "psa_rate_pct", "p_value"])
sub["lift_pp"] = sub.ad_rate_pct - sub.psa_rate_pct
sub["p_bonferroni"] = (sub.p_value * len(sub)).clip(upper=1)
sub["significant_after_correction"] = sub.p_bonferroni < 0.05
print(sub.round(4).to_string(index=False))
print("subgroup tests: %d | significant raw (p<0.05): %d | significant after Bonferroni: %d"
      % (len(sub), (sub.p_value < 0.05).sum(), sub.significant_after_correction.sum()))
sub.to_csv(OUT / "subgroup_tests.csv", index=False)

# ----- charts -----
fig, ax = plt.subplots(figsize=(7, 4.2))
rates = [100 * p_psa, 100 * p_ad]
errs = [[100 * (p_psa - ci_psa[0]), 100 * (p_ad - ci_ad[0])], [100 * (ci_psa[1] - p_psa), 100 * (ci_ad[1] - p_ad)]]
bars = ax.bar(["PSA (control)\nn = %s" % f"{n_psa:,}", "Ad\nn = %s" % f"{n_ad:,}"], rates,
              color=[MUTED, BLUE], width=0.5, yerr=errs, capsize=5, error_kw={"ecolor": INK, "linewidth": 1.2})
for b, v in zip(bars, rates):
    ax.text(b.get_x() + b.get_width() / 2 + 0.28, v, f"{v:.2f}%", va="center", color=INK, fontsize=10)
ax.set_ylim(0, 3.2)
ax.set_ylabel("Conversion rate (%)")
ax.set_title("The ad converted 0.77 points better than the PSA", loc="left", color=INK, fontsize=12, fontweight="bold")
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
fig.text(0.01, 0.01, "Bars show conversion rate; whiskers are 95% confidence intervals.", color=MUTED, fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(OUT / "chart_conversion_by_group.png")
plt.close(fig)

fig, ax = plt.subplots(figsize=(8, 4.2))
d = dose.pivot(index="ads_bucket", columns="group", values="mean")
xpos = np.arange(len(d))
ax.plot(xpos, d["ad"], color=BLUE, marker="o", linewidth=2, label="Ad")
ax.plot(xpos, d["psa"], color=MUTED, marker="o", linewidth=2, label="PSA (control)")
ax.set_xticks(xpos, d.index)
ax.set_xlabel("Total ads the user saw")
ax.set_ylabel("Conversion rate (%)")
ax.legend(frameon=False)
ax.set_title("The ad's advantage only shows up for users who saw 26+ ads", loc="left", color=INK, fontsize=12, fontweight="bold")
ax.grid(axis="y", color=GRID, linewidth=0.8)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(OUT / "chart_conversion_by_ads_seen.png")
plt.close(fig)
print("\nSaved charts and tables to", OUT)
