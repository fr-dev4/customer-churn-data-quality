"""Data Quality & Exploratory Analysis - customer churn sample.
Run: python clean_and_analyze.py   (needs pandas, matplotlib, openpyxl)
Outputs: customer_churn_clean.csv, data_dictionary.csv, churn_data_quality.xlsx, charts/*.png
"""
import pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAW = "customer_churn_sample_raw.csv"
raw = pd.read_csv(RAW)
df = raw.copy()
checks, log = [], []

def check(name, passed, detail=""):
    checks.append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})

# ---------- 1. PROFILE ----------
profile = pd.DataFrame({
    "dtype": raw.dtypes.astype(str),
    "non_null": raw.notna().sum(),
    "missing": raw.isna().sum(),
    "unique": raw.nunique(),
    "min": raw.min(numeric_only=True),
    "max": raw.max(numeric_only=True),
})
profile.index.name = "column"

# IQR outlier scan on numeric columns
outliers = []
for c in ["Age", "TenureMonths", "MonthlyCharges", "TotalCharges", "SupportTickets"]:
    q1, q3 = raw[c].quantile([.25, .75]); iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    bad = raw[(raw[c] < lo) | (raw[c] > hi)]
    outliers.append({"column": c, "lower_fence": round(lo, 2), "upper_fence": round(hi, 2),
                     "n_outliers": len(bad), "ids": ", ".join(bad.CustomerID)})
outliers = pd.DataFrame(outliers)

dups_full = int(raw.duplicated().sum())
dups_id = int(raw.CustomerID.duplicated().sum())

# ---------- 2. CLEAN ----------
# a) trim whitespace + standardise text case (no-op on this file, but protects re-runs on new data)
text_cols = df.select_dtypes(include=["object", "string"]).columns
changed = 0
for c in text_cols:
    new = df[c].astype(str).str.strip()
    changed += int((new != df[c]).sum()); df[c] = new
log.append(("Trim whitespace in text columns", f"{changed} cells changed"))

# b) duplicates
df = df.drop_duplicates(subset="CustomerID")
log.append(("Drop duplicate CustomerID rows", f"{len(raw) - len(df)} rows removed"))

# c) types + derived fields
df["Churn_Flag"] = (df.Churn == "Yes").astype(int)
df["ExpectedTotal"] = (df.TenureMonths * df.MonthlyCharges).round(2)
df["TotalCharges_Diff"] = (df.TotalCharges - df.ExpectedTotal).round(2)
df["TenureBand"] = pd.cut(df.TenureMonths, [0, 6, 12, 24, 48],
                          labels=["0-6", "7-12", "13-24", "25-48"])
df["AgeBand"] = pd.cut(df.Age, [17, 30, 40, 50, 70], labels=["18-30", "31-40", "41-50", "51+"])
log.append(("Add Churn_Flag (0/1)", "Yes->1, No->0 for averaging"))
log.append(("Add TenureBand and AgeBand", "Binned for distribution views"))
log.append(("Add ExpectedTotal / TotalCharges_Diff", "Tenure x MonthlyCharges reconciliation"))

# ---------- 3. VALIDATE ----------
check("No missing values", df.isna().sum().sum() == 0)
check("CustomerID unique", df.CustomerID.is_unique)
check("No fully duplicated rows", dups_full == 0)
check("Age within 18-100", df.Age.between(18, 100).all(), f"range {df.Age.min()}-{df.Age.max()}")
check("TenureMonths > 0", (df.TenureMonths > 0).all())
check("MonthlyCharges > 0", (df.MonthlyCharges > 0).all())
check("SupportTickets >= 0", (df.SupportTickets >= 0).all())
check("Gender in {Male, Female}", df.Gender.isin(["Male", "Female"]).all())
check("Churn in {Yes, No}", df.Churn.isin(["Yes", "No"]).all())
check("TotalCharges = Tenure x Monthly (+-0.01)", (df.TotalCharges_Diff.abs() <= 0.01).all(),
      f"max abs diff {df.TotalCharges_Diff.abs().max()}")
check("One price per SubscriptionType", (df.groupby("SubscriptionType").MonthlyCharges.nunique() == 1).all())
check("Row count preserved", len(df) == len(raw), f"{len(raw)} -> {len(df)}")
checks_df = pd.DataFrame(checks)

# ---------- 4. EXPLORE ----------
num = ["Age", "TenureMonths", "MonthlyCharges", "TotalCharges", "SupportTickets"]
summary = df[num].describe().T.round(2)
summary["median"] = df[num].median().round(2)
churn_rate = df.Churn_Flag.mean()

def rate(col):
    g = df.groupby(col, observed=True).agg(customers=("Churn_Flag", "size"),
                                          churned=("Churn_Flag", "sum"),
                                          churn_rate=("Churn_Flag", "mean"))
    g["churn_rate"] = (g.churn_rate * 100).round(1)
    return g
segments = {c: rate(c) for c in ["ContractType", "SubscriptionType", "PaymentMethod",
                                 "TenureBand", "AgeBand", "Gender", "SupportTickets"]}
by_churn = df.groupby("Churn")[["Age", "TenureMonths", "MonthlyCharges", "SupportTickets"]].mean().round(2)

# ---------- 5. CHARTS ----------
plt.rcParams.update({"figure.figsize": (6, 3.6), "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(1, 3, figsize=(13, 3.4))
for a, c in zip(ax, ["Age", "TenureMonths", "MonthlyCharges"]):
    a.hist(df[c], bins=6, color="#4C78A8", edgecolor="white"); a.set_title(f"Distribution of {c}")
plt.tight_layout(); plt.savefig("charts/distributions.png", dpi=130); plt.close()

fig, ax = plt.subplots(1, 4, figsize=(14, 3.4))
for a, c in zip(ax, ["ContractType", "SubscriptionType", "PaymentMethod", "TenureBand"]):
    s = segments[c].churn_rate; a.bar(s.index.astype(str), s.values, color="#E45756")
    a.set_ylim(0, 105); a.set_title(f"Churn % by {c}"); a.tick_params(axis="x", rotation=30)
plt.tight_layout(); plt.savefig("charts/churn_by_segment.png", dpi=130); plt.close()

fig, ax = plt.subplots(1, 3, figsize=(12, 3.4))
for a, c in zip(ax, ["Age", "TenureMonths", "SupportTickets"]):
    df.boxplot(column=c, by="Churn", ax=a, grid=False); a.set_title(c); a.set_xlabel("Churn")
plt.suptitle(""); plt.tight_layout(); plt.savefig("charts/boxplots_by_churn.png", dpi=130); plt.close()

# ---------- 6. EXPORT ----------
df.to_csv("customer_churn_clean.csv", index=False)
dictionary = pd.DataFrame([
 ("CustomerID","text","Unique customer key (CUST-####)","Raw"),
 ("Gender","category","Male / Female","Raw"),
 ("Age","int","Customer age in years (23-60 in sample)","Raw"),
 ("TenureMonths","int","Months as a customer","Raw"),
 ("SubscriptionType","category","Basic / Pro / Enterprise plan","Raw"),
 ("MonthlyCharges","float","Monthly price; fixed per plan (49.99 / 79.99 / 149.99)","Raw"),
 ("TotalCharges","float","Lifetime billed amount; equals Tenure x MonthlyCharges","Raw"),
 ("ContractType","category","Month-to-Month / One Year / Two Year","Raw"),
 ("SupportTickets","int","Number of support tickets raised","Raw"),
 ("PaymentMethod","category","Credit Card / Debit Card / Bank Transfer / UPI","Raw"),
 ("Churn","category","Yes = customer left, No = retained","Raw"),
 ("Churn_Flag","int","1 if Churn = Yes else 0","Derived"),
 ("ExpectedTotal","float","TenureMonths x MonthlyCharges","Derived"),
 ("TotalCharges_Diff","float","TotalCharges - ExpectedTotal (0 = reconciles)","Derived"),
 ("TenureBand","category","0-6 / 7-12 / 13-24 / 25-48 months","Derived"),
 ("AgeBand","category","18-30 / 31-40 / 41-50 / 51+","Derived"),
], columns=["column","type","description","origin"])
dictionary.to_csv("data_dictionary.csv", index=False)

with pd.ExcelWriter("churn_data_quality.xlsx") as xw:
    profile.to_excel(xw, sheet_name="Profile")
    outliers.to_excel(xw, sheet_name="Outliers", index=False)
    pd.DataFrame(log, columns=["step", "result"]).to_excel(xw, sheet_name="Cleaning_Log", index=False)
    checks_df.to_excel(xw, sheet_name="Validation", index=False)
    summary.to_excel(xw, sheet_name="Summary_Stats")
    r = 0
    for k, v in segments.items():
        v.to_excel(xw, sheet_name="Churn_by_Segment", startrow=r); r += len(v) + 3
    by_churn.to_excel(xw, sheet_name="Churners_vs_Retained")
    df.to_excel(xw, sheet_name="Clean_Data", index=False)
    dictionary.to_excel(xw, sheet_name="Data_Dictionary", index=False)

# ---------- console report ----------
pd.set_option("display.width", 200)
print(profile, "\n", outliers, f"\nDup rows {dups_full}, dup IDs {dups_id}\n", checks_df.to_string(),
      "\n", summary, f"\nOverall churn {churn_rate:.1%}\n", by_churn)
for k, v in segments.items(): print("\n", v)
