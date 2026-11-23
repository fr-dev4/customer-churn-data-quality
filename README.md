# Data Quality & Exploratory Analysis: Customer Churn Sample

**Dataset:** `customer_churn_sample_raw.csv` (15 customers, 11 columns, synthetic)
**Reproduce:** `python clean_and_analyze.py` (pandas, matplotlib, openpyxl)

## Files
| File | Purpose |
|---|---|
| `clean_and_analyze.py` | Full pipeline: profile, clean, validate, explore, export |
| `churn_data_quality.xlsx` | Workbook: Profile, Outliers, Cleaning_Log, Validation, Summary_Stats, Churn_by_Segment, Clean_Data, Data_Dictionary |
| `customer_churn_clean.csv` | Analysis-ready dataset (raw columns + 5 derived columns) |
| `data_dictionary.csv` | Column definitions |
| `charts/` | Distributions, churn by segment, boxplots by churn |

## 1. Profile
- **Shape / types:** 15 rows x 11 columns; 5 numeric, 6 text/categorical. Types were already correct.
- **Missing values:** none in any column.
- **Duplicates:** 0 duplicate rows, 0 duplicate `CustomerID`s.
- **Outliers (1.5 x IQR rule):** none in Age, TenureMonths, MonthlyCharges, TotalCharges or SupportTickets. The largest values (Tenure 48, TotalCharges 7,199.52) are legitimate Enterprise customers.
- **Categories:** all clean, no spelling or case variants (Gender 2, Subscription 3, Contract 3, Payment 4, Churn 2).

## 2. Cleaning decisions and assumptions
| Decision | Reason |
|---|---|
| No rows removed, no values imputed | Nothing failed a quality rule, and with n=15 dropping rows would be costly |
| Whitespace trim + duplicate-ID drop kept in the script | No-ops here (0 changes), but make the pipeline safe for a larger refresh |
| Added `Churn_Flag` (0/1) | Lets churn rate be averaged directly |
| Added `TenureBand`, `AgeBand` | Binning for distribution/segment views |
| Added `ExpectedTotal`, `TotalCharges_Diff` | Reconciliation check on billing |
| Assumed `TotalCharges = TenureMonths x MonthlyCharges` | Holds exactly for all 15 rows |
| Assumed one fixed price per plan | Basic 49.99, Pro 79.99, Enterprise 149.99 |

## 3. Validation checks (12/12 pass)
No nulls; unique IDs; no duplicate rows; Age 18-100 (observed 23-60); Tenure > 0; MonthlyCharges > 0; SupportTickets >= 0; valid Gender and Churn values; TotalCharges reconciles (max difference 0.00); one price per plan; row count preserved (15 -> 15).

## 4. Summary statistics
| Column | Mean | Median | Min | Max |
|---|---|---|---|---|
| Age | 39.1 | 38 | 23 | 60 |
| TenureMonths | 18.8 | 15 | 2 | 48 |
| MonthlyCharges | 84.66 | 79.99 | 49.99 | 149.99 |
| TotalCharges | 2,088.48 | 1,099.78 | 99.98 | 7,199.52 |
| SupportTickets | 2.5 | 2 | 0 | 6 |

Overall churn: **7 of 15 customers (46.7%)**. Tenure, TotalCharges and MonthlyCharges are right-skewed (a few long-tenure Enterprise customers pull the mean above the median).

## 5. Initial patterns
| Segment | Churn rate |
|---|---|
| Month-to-Month contract | 7/7 (100%) |
| One Year / Two Year | 0/4, 0/4 (0%) |
| Basic / Pro / Enterprise | 71% / 50% / 0% |
| Tenure 0-12 months | 6/6 (100%) |
| Tenure 25-48 months | 0/4 (0%) |
| Age 18-30 | 4/4 (100%) |
| 3+ support tickets | 7/7 (100%) |
| 0-2 support tickets | 0/8 (0%) |
| Bank Transfer / Credit Card / UPI / Debit Card | 0% / 33% / 75% / 100% |
| Gender (F / M) | 50% / 43% (no meaningful gap) |

Churners average 30 years old, 7 months tenure, 58.56 monthly charge and 4.3 tickets. Retained customers average 47 years, 29 months, 107.49 and 1.0 tickets.

## 6. Limitations (read before drawing conclusions)
- **n = 15 is too small for statistical conclusions.** The 100%/0% splits are descriptive only and would not hold up in a larger sample.
- **Predictors overlap.** Contract type, plan, tenure and age move together, so these patterns cannot be separated from each other here.
- **Support tickets** may be a symptom of an unhappy customer rather than a cause. The data cannot tell us which.
- The dataset is synthetic and unusually tidy, so a clean audit result mainly shows the validation rules work, not that real data would be this clean.
- **Next steps:** repeat on a larger real extract; add contract start/end dates to check tenure against contract length.
