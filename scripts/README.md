# Scripts

## export_kline.py

导出 `kline_data` 表中所有日 K 线到 CSV 文件。

输出到 `data/kline-d/`，每只股票一个文件，命名格式 `{symbol}-{start}-{end}.csv`。

```bash
# 导出全部
python scripts/export_kline.py

# 导出单只股票
python scripts/export_kline.py --symbol SH.600519

# 只导出前 N 只（测试用）
python scripts/export_kline.py --limit 10
```

## ingest_financial.py

从通达信财务数据文件（.zip / .dat）导入财务数据到 6 张财务数据表。

需要先通过 mootdx 下载数据文件到 `data/affair/` 目录。

```bash
# 指定报告期
python scripts/ingest_financial.py --period=20260331

# 指定文件路径
python scripts/ingest_financial.py --file=/path/to/gpcw20260331.zip

# 批量导入 data/affair/ 下所有 gpcw*.zip 文件
python scripts/ingest_financial.py --all
```

## import_kline.py

将 `export_kline.py` 导出的 CSV 文件重新导入 `kline_data` 表。

自动从文件名解析 symbol（`{symbol}-{start}-{end}.csv`），支持 `--dry-run` 预览。

```bash
# 导入全部 CSV
python scripts/import_kline.py

# 预览（只统计行数，不写入 DB）
python scripts/import_kline.py --dry-run

# 导入指定文件/通配符
python scripts/import_kline.py data/kline-d/SH.6005*.csv
```

## init_db.sql

建表 DDL — 创建 TimescaleDB 超表：`kline_data`、`corporate_events`、`trade_calendar`、`api_request_log`。

```bash
psql -d candlex -f scripts/init_db.sql
```

## init_financial_v2_tables.sql

创建 6 张财务数据明细表的 DDL。

```bash
psql -d candlex -f scripts/init_financial_v2_tables.sql
```
