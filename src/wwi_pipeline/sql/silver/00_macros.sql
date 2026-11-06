-- Reusable parsing macros used by the bronze -> silver load.
-- Bronze keeps every value as VARCHAR exactly as found in the CSV; these macros
-- convert them to proper types.  Empty strings become NULL; values that cannot
-- be parsed also become NULL (and are counted / quarantined by the loader).
CREATE SCHEMA IF NOT EXISTS util;

CREATE OR REPLACE MACRO util.clean(x) AS nullif(trim(x), '');

-- '1.0' (pandas float export of nullable integers) -> 1 ; '1.5' -> NULL
CREATE OR REPLACE MACRO util.to_bigint(x) AS (
    CASE
        WHEN TRY_CAST(util.clean(x) AS DOUBLE) = floor(TRY_CAST(util.clean(x) AS DOUBLE))
        THEN TRY_CAST(TRY_CAST(util.clean(x) AS DOUBLE) AS BIGINT)
    END
);

CREATE OR REPLACE MACRO util.to_bool(x) AS (
    CASE lower(util.clean(x))
        WHEN 'true' THEN TRUE  WHEN '1' THEN TRUE  WHEN 't' THEN TRUE  WHEN 'yes' THEN TRUE
        WHEN 'false' THEN FALSE WHEN '0' THEN FALSE WHEN 'f' THEN FALSE WHEN 'no' THEN FALSE
    END
);

-- The Kaggle export uses day-first dates (dd-mm-yyyy hh:mm[:ss]); ISO formats are
-- accepted too so that other exports of the same dataset can be ingested.
CREATE OR REPLACE MACRO util.to_ts(x) AS try_strptime(
    util.clean(x),
    ['%d-%m-%Y %H:%M:%S', '%d-%m-%Y %H:%M', '%d-%m-%Y',
     '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d']
);
