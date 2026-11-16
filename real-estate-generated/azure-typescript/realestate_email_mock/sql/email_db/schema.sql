DO $$ BEGIN CREATE TYPE "delivery_status" AS ENUM ('delivered', 'bounced'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "outbounds" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "recipient" VARCHAR(200) NOT NULL,
    "subject" VARCHAR(200) NOT NULL,
    "body" VARCHAR(2000) NOT NULL,
    "status" "delivery_status" NOT NULL,
    "delivery_id" VARCHAR(40) NOT NULL,
    "idempotency_key" VARCHAR(120) NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "api_keys" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "key_hash" VARCHAR(64) NOT NULL,
    "owner_id" UUID NOT NULL,
    "scopes" JSONB NOT NULL DEFAULT '[]',
    "is_active" BOOLEAN NOT NULL DEFAULT (TRUE),
    "expires_at" TIMESTAMPTZ,
    "last_used_at" TIMESTAMPTZ,
    PRIMARY KEY ("id")
);

ALTER TABLE "outbounds" ADD CONSTRAINT "chk_outbounds_body_5154484f" CHECK ((char_length("body") <= 2000));

ALTER TABLE "outbounds" ADD CONSTRAINT "chk_outbounds_delivery_id_38a6dcbb" CHECK ((char_length("delivery_id") <= 40));

ALTER TABLE "outbounds" ADD CONSTRAINT "chk_outbounds_idempotency_key_8c42382d" CHECK ((char_length("idempotency_key") <= 120));

ALTER TABLE "outbounds" ADD CONSTRAINT "chk_outbounds_recipient_118cdbab" CHECK ((char_length("recipient") <= 200));

ALTER TABLE "outbounds" ADD CONSTRAINT "chk_outbounds_subject_6afca0bc" CHECK ((char_length("subject") <= 200));

ALTER TABLE "api_keys" ADD CONSTRAINT "chk_api_keys_key_hash_455a30f8" CHECK ((char_length("key_hash") <= 64));

ALTER TABLE "outbounds" ADD CONSTRAINT "uq_outbounds_delivery_id" UNIQUE ("delivery_id");

ALTER TABLE "outbounds" ADD CONSTRAINT "uq_outbounds_idempotency_key" UNIQUE ("idempotency_key");

CREATE INDEX "ix_api_keys_owner_id" ON "api_keys" ("owner_id");

ALTER TABLE "api_keys" ADD CONSTRAINT "uq_api_keys_key_hash" UNIQUE ("key_hash");

COMMENT ON TABLE "outbounds" IS 'An email the vendor accepted.';

COMMENT ON TABLE "api_keys" IS 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.';
