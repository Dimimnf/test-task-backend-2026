-- Начальная схема новой PostgreSQL-БД по моделям из каталога models.
BEGIN;

CREATE TABLE IF NOT EXISTS abstract_customer (
    id BIGSERIAL NOT NULL,
    send_methods JSONB,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT pk_abstract_customer PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS amo_company (
    id BIGINT NOT NULL,
    name VARCHAR NOT NULL,
    inn VARCHAR,
    api_value JSONB,
    CONSTRAINT pk_amo_company PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS amo_contact (
    id BIGINT NOT NULL,
    name VARCHAR NOT NULL,
    phone VARCHAR,
    api_value JSONB,
    CONSTRAINT pk_amo_contact PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS amo_customer (
    id BIGINT NOT NULL,
    abstract_customer_id BIGINT NOT NULL,
    login VARCHAR,
    name VARCHAR NOT NULL,
    api_value JSONB,
    CONSTRAINT pk_amo_customer PRIMARY KEY (id),
    CONSTRAINT fk_amo_customer_abstract_customer_id_abstract_customer
        FOREIGN KEY (abstract_customer_id)
        REFERENCES abstract_customer (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS amo_lead (
    id BIGINT NOT NULL,
    abstract_customer_id BIGINT NOT NULL,
    login VARCHAR,
    name VARCHAR NOT NULL,
    api_value JSONB,
    CONSTRAINT pk_amo_lead PRIMARY KEY (id),
    CONSTRAINT fk_amo_lead_abstract_customer_id_abstract_customer
        FOREIGN KEY (abstract_customer_id)
        REFERENCES abstract_customer (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS abstract_customer_company (
    abstract_customer_id BIGINT NOT NULL,
    amo_company_id BIGINT NOT NULL,
    CONSTRAINT pk_abstract_customer_company
        PRIMARY KEY (abstract_customer_id, amo_company_id),
    CONSTRAINT fk_abstract_customer_company_abstract_customer_id_abstr_7059
        FOREIGN KEY (abstract_customer_id)
        REFERENCES abstract_customer (id) ON DELETE CASCADE,
    CONSTRAINT fk_abstract_customer_company_amo_company_id_amo_company
        FOREIGN KEY (amo_company_id)
        REFERENCES amo_company (id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS abstract_customer_contact (
    abstract_customer_id BIGINT NOT NULL,
    amo_contact_id BIGINT NOT NULL,
    CONSTRAINT pk_abstract_customer_contact
        PRIMARY KEY (abstract_customer_id, amo_contact_id),
    CONSTRAINT fk_abstract_customer_contact_abstract_customer_id_abstr_bb98
        FOREIGN KEY (abstract_customer_id)
        REFERENCES abstract_customer (id) ON DELETE CASCADE,
    CONSTRAINT fk_abstract_customer_contact_amo_contact_id_amo_contact
        FOREIGN KEY (amo_contact_id)
        REFERENCES amo_contact (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_amo_company_name ON amo_company (name);
CREATE INDEX IF NOT EXISTS ix_amo_company_inn ON amo_company (inn);
CREATE INDEX IF NOT EXISTS ix_amo_contact_phone ON amo_contact (phone);
CREATE INDEX IF NOT EXISTS ix_amo_customer_abstract_customer_id
    ON amo_customer (abstract_customer_id);
CREATE INDEX IF NOT EXISTS ix_amo_customer_login ON amo_customer (login);
CREATE INDEX IF NOT EXISTS ix_amo_lead_abstract_customer_id
    ON amo_lead (abstract_customer_id);
CREATE INDEX IF NOT EXISTS ix_amo_lead_login ON amo_lead (login);

COMMIT;
