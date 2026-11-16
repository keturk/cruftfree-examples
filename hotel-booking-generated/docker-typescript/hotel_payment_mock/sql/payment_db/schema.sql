DO $$ BEGIN CREATE TYPE "charge_status" AS ENUM ('succeeded', 'declined', 'refunded'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "card_charges" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "reference" VARCHAR(80) NOT NULL,
    "amount" DECIMAL(19,4) NOT NULL,
    "currency" VARCHAR(3) NOT NULL,
    "status" "charge_status" NOT NULL,
    "decline_reason" VARCHAR(200),
    "charge_id" VARCHAR(40) NOT NULL,
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

ALTER TABLE "card_charges" ADD CONSTRAINT "chk_card_charges_charge_id_fb5588e1" CHECK ((char_length("charge_id") <= 40));

ALTER TABLE "card_charges" ADD CONSTRAINT "chk_card_charges_currency_011ea433" CHECK ((char_length("currency") <= 3));

ALTER TABLE "card_charges" ADD CONSTRAINT "chk_card_charges_decline_reason_5db38c9a" CHECK ((char_length("decline_reason") <= 200));

ALTER TABLE "card_charges" ADD CONSTRAINT "chk_card_charges_idempotency_key_8c42382d" CHECK ((char_length("idempotency_key") <= 120));

ALTER TABLE "card_charges" ADD CONSTRAINT "chk_card_charges_reference_32bbf114" CHECK ((char_length("reference") <= 80));

ALTER TABLE "api_keys" ADD CONSTRAINT "chk_api_keys_key_hash_455a30f8" CHECK ((char_length("key_hash") <= 64));

ALTER TABLE "card_charges" ADD CONSTRAINT "uq_card_charges_charge_id" UNIQUE ("charge_id");

ALTER TABLE "card_charges" ADD CONSTRAINT "uq_card_charges_idempotency_key" UNIQUE ("idempotency_key");

CREATE INDEX "ix_api_keys_owner_id" ON "api_keys" ("owner_id");

ALTER TABLE "api_keys" ADD CONSTRAINT "uq_api_keys_key_hash" UNIQUE ("key_hash");

COMMENT ON TABLE "card_charges" IS 'A charge the vendor answered.';

COMMENT ON TABLE "api_keys" IS 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.';
