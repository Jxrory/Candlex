CREATE TABLE IF NOT EXISTS kline_data (
    symbol        TEXT    NOT NULL,
    date          DATE    NOT NULL,
    open          NUMERIC(10,3),
    high          NUMERIC(10,3),
    low           NUMERIC(10,3),
    close         NUMERIC(10,3),
    volume        BIGINT,
    amount        NUMERIC(15,2),
    factor_qfq    NUMERIC(10,6),
    factor_hfq    NUMERIC(10,6),
    source        TEXT    NOT NULL,
    updated_at    TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (symbol, date)
);

SELECT create_hypertable('kline_data', 'date', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_kline_symbol_date ON kline_data (symbol, date DESC);

CREATE TABLE IF NOT EXISTS trade_calendar (
    trade_date  DATE  PRIMARY KEY,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('trade_calendar', 'trade_date', if_not_exists => TRUE);
