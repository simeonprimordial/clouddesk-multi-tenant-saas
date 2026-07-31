CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE tenant_status AS ENUM (
    'active',
    'inactive',
    'suspended'
);

CREATE TYPE user_status AS ENUM (
    'active',
    'inactive'
);

CREATE TYPE tenant_role AS ENUM (
    'owner',
    'admin',
    'member'
);

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status tenant_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT tenants_name_not_empty
        CHECK (LENGTH(TRIM(name)) > 0),

    CONSTRAINT tenants_slug_not_empty
        CHECK (LENGTH(TRIM(slug)) > 0)
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cognito_user_id UUID UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT users_email_not_empty
        CHECK (LENGTH(TRIM(email)) > 0),

    CONSTRAINT users_first_name_not_empty
        CHECK (LENGTH(TRIM(first_name)) > 0),

    CONSTRAINT users_last_name_not_empty
        CHECK (LENGTH(TRIM(last_name)) > 0)
);

CREATE TABLE tenant_users (
    tenant_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role tenant_role NOT NULL DEFAULT 'member',
    status user_status NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT tenant_users_primary_key
        PRIMARY KEY (tenant_id, user_id),

    CONSTRAINT tenant_users_tenant_fk
        FOREIGN KEY (tenant_id)
        REFERENCES tenants(id)
        ON DELETE CASCADE,

    CONSTRAINT tenant_users_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_tenants_name
    ON tenants (name);

CREATE INDEX idx_tenant_users_user_id
    ON tenant_users (user_id);

CREATE INDEX idx_tenant_users_tenant_status
    ON tenant_users (tenant_id, status);

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tenants_set_updated_at
BEFORE UPDATE ON tenants
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER tenant_users_set_updated_at
BEFORE UPDATE ON tenant_users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

