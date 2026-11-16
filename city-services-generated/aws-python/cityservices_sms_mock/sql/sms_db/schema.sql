DO $$ BEGIN CREATE TYPE "text_status" AS ENUM ('accepted', 'delivered', 'failed'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "sent_sms" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "message_id" VARCHAR(40) NOT NULL,
    "idempotency_key" VARCHAR(120) NOT NULL,
    "recipient" VARCHAR(20) NOT NULL,
    "body" VARCHAR(320) NOT NULL,
    "status" "text_status" NOT NULL DEFAULT ('delivered'),
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

ALTER TABLE "sent_sms" ADD CONSTRAINT "chk_sent_sms_body_5f5b8941" CHECK ((char_length("body") <= 320));

ALTER TABLE "sent_sms" ADD CONSTRAINT "chk_sent_sms_idempotency_key_8c42382d" CHECK ((char_length("idempotency_key") <= 120));

ALTER TABLE "sent_sms" ADD CONSTRAINT "chk_sent_sms_message_id_7a974951" CHECK ((char_length("message_id") <= 40));

ALTER TABLE "api_keys" ADD CONSTRAINT "chk_api_keys_key_hash_455a30f8" CHECK ((char_length("key_hash") <= 64));

ALTER TABLE "sent_sms" ADD CONSTRAINT "uq_sent_sms_message_id" UNIQUE ("message_id");

ALTER TABLE "sent_sms" ADD CONSTRAINT "uq_sent_sms_idempotency_key" UNIQUE ("idempotency_key");

CREATE INDEX "ix_api_keys_owner_id" ON "api_keys" ("owner_id");

ALTER TABLE "api_keys" ADD CONSTRAINT "uq_api_keys_key_hash" UNIQUE ("key_hash");

COMMENT ON TABLE "sent_sms" IS 'A text the vendor accepted.';

COMMENT ON TABLE "api_keys" IS 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.';
