# CandleX

A-stock data service: K-line, financial data, trading calendar, dividends, and news.

## Language

命令行中的交互和输出文档请使用中文

**Financial Query**:
Cross-stock screening endpoint (`/v2/financial/query`) that returns financial data grouped by symbol.
_Avoid_: flat list, raw query

**Report Date (`report_date`)**:
A reporting period end date — always one of 03-31, 06-30, 09-30, 12-31 (quarter ends).
_Avoid_: date range, arbitrary date

**Last N Quarters**:
Default scope for screening queries; computes the N most recently completed quarter-end dates from calendar, not from DB. Currently N=4.
_Avoid_: past 365 days, last calendar year

**Screen Filter**:
A min/max value constraint on a financial indicator (e.g., `roe_min=15`, `debt_ratio_max=50`). No filters means no results.
_Avoid_: search, query param
