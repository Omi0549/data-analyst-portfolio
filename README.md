# Data Analyst Portfolio

Projects by Om Biswal (BS astrophysics, Arizona State University). Each project starts from a business-style question, uses a public dataset, and reports findings that were checked by running the code.

## Projects

| Project | Question | Tools | Key finding |
|---|---|---|---|
| [Olist SQL analysis](olist-sql-analysis/) | What drives customer satisfaction and revenue on a Brazilian e-commerce marketplace? | SQL (SQLite), Python, Tableau Public | 8.1% of delivered orders arrive late; late orders average 2.57 stars vs 4.29 on time |
| [Olist Tableau dashboard](olist-sql-analysis/#interactive-dashboard) | The same findings as an interactive view | Tableau Public | [Live dashboard](https://public.tableau.com/app/profile/om.biswal/viz/Olist_dashboard_17937939194590/OlistDashboard) |
| [NYC yellow taxi analysis](nyc-taxi-postgres/) | When and where do taxi trips happen, and what drives fares and tips? | PostgreSQL, SQL window functions, Python | 10.1M trips analysed; airport trips pay $56 vs $18 on average but earn less per mile ($4.31 vs $6.67) |
| [Marketing A/B test](ab-test-marketing/) | Did the ad campaign lift conversion compared with a PSA control? | Python (pandas, scipy, statsmodels) | Ad lifted conversion by 0.77 points (95% CI 0.59 to 0.94), but only for users who saw 25+ ads |

## Running the projects

Each project folder has its own README with data source, method, findings and reproduction steps. Raw datasets are not stored in this repo; each README links to the source (Kaggle). Python dependencies are in `requirements.txt`:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Data licenses

- Olist Brazilian E-Commerce: CC BY-NC-SA 4.0 (non-commercial, attribution required).
- Marketing A/B Testing: CC0.
