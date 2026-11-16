DO $$ BEGIN CREATE TYPE "envelope_status" AS ENUM ('sent', 'signed', 'declined'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "vendor_envelopes" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "signer_name" VARCHAR(200) NOT NULL,
    "document_title" VARCHAR(200) NOT NULL,
    "status" "envelope_status" NOT NULL DEFAULT ('sent'),
    "settled_at" TIMESTAMPTZ,
    "document_body" TEXT NOT NULL,
    "signer_email" VARCHAR(320) NOT NULL,
    "envelope_id" VARCHAR(40) NOT NULL,
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

ALTER TABLE "vendor_envelopes" ADD CONSTRAINT "chk_vendor_envelopes_document_title_2616e072" CHECK ((char_length("document_title") <= 200));

ALTER TABLE "vendor_envelopes" ADD CONSTRAINT "chk_vendor_envelopes_envelope_id_f51afe7b" CHECK ((char_length("envelope_id") <= 40));

ALTER TABLE "vendor_envelopes" ADD CONSTRAINT "chk_vendor_envelopes_idempotency_key_8c42382d" CHECK ((char_length("idempotency_key") <= 120));

ALTER TABLE "vendor_envelopes" ADD CONSTRAINT "chk_vendor_envelopes_signer_name_27552856" CHECK ((char_length("signer_name") <= 200));

ALTER TABLE "api_keys" ADD CONSTRAINT "chk_api_keys_key_hash_455a30f8" CHECK ((char_length("key_hash") <= 64));

ALTER TABLE "vendor_envelopes" ADD CONSTRAINT "uq_vendor_envelopes_envelope_id" UNIQUE ("envelope_id");

ALTER TABLE "vendor_envelopes" ADD CONSTRAINT "uq_vendor_envelopes_idempotency_key" UNIQUE ("idempotency_key");

CREATE INDEX "ix_api_keys_owner_id" ON "api_keys" ("owner_id");

ALTER TABLE "api_keys" ADD CONSTRAINT "uq_api_keys_key_hash" UNIQUE ("key_hash");

COMMENT ON TABLE "vendor_envelopes" IS 'A document waiting for a signature.';

COMMENT ON TABLE "api_keys" IS 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.';
