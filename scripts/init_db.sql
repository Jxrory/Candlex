CREATE TABLE IF NOT EXISTS kline_data (
    symbol      TEXT    NOT NULL,
    date        DATE    NOT NULL,
    open        NUMERIC(10,3),
    high        NUMERIC(10,3),
    low         NUMERIC(10,3),
    close       NUMERIC(10,3),
    volume      BIGINT,
    amount      NUMERIC(15,2),
    source      TEXT    NOT NULL,
    PRIMARY KEY (symbol, date)
);

SELECT create_hypertable('kline_data', 'date', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_kline_symbol_date ON kline_data (symbol, date DESC);

CREATE TABLE IF NOT EXISTS corporate_events (
    symbol            TEXT    NOT NULL,
    ex_date           DATE    NOT NULL,
    cash_dividend     NUMERIC(10,6),
    stock_dividend    NUMERIC(10,6),
    capitalization    NUMERIC(10,6),
    rights_ratio      NUMERIC(10,6),
    rights_price      NUMERIC(10,4),
    prev_close        NUMERIC(10,3),
    adj_ratio         NUMERIC(10,6),
    event_type        TEXT    NOT NULL,
    source            TEXT    NOT NULL,
    PRIMARY KEY (symbol, ex_date, event_type)
);

SELECT create_hypertable('corporate_events', 'ex_date', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS trade_calendar (
    trade_date  DATE  PRIMARY KEY,
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

SELECT create_hypertable('trade_calendar', 'trade_date', if_not_exists => TRUE);
