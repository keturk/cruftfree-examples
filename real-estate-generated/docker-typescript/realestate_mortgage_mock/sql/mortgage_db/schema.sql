DO $$ BEGIN CREATE TYPE "preapproval_decision" AS ENUM ('approved', 'declined'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "lender_answers" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "applicant_name" VARCHAR(200) NOT NULL,
    "amount" DECIMAL(19,4) NOT NULL,
    "decision" "preapproval_decision" NOT NULL,
    "reference" VARCHAR(40) NOT NULL,
    "idempotency_key" VARCHAR(120) NOT NULL,
    "applicant_email" VARCHAR(320) NOT NULL,
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

ALTER TABLE "lender_answers" ADD CONSTRAINT "chk_lender_answers_applicant_name_5cf1d443" CHECK ((char_length("applicant_name") <= 200));

ALTER TABLE "lender_answers" ADD CONSTRAINT "chk_lender_answers_idempotency_key_8c42382d" CHECK ((char_length("idempotency_key") <= 120));

ALTER TABLE "lender_answers" ADD CONSTRAINT "chk_lender_answers_reference_2a8e3098" CHECK ((char_length("reference") <= 40));

ALTER TABLE "api_keys" ADD CONSTRAINT "chk_api_keys_key_hash_455a30f8" CHECK ((char_length("key_hash") <= 64));

ALTER TABLE "lender_answers" ADD CONSTRAINT "uq_lender_answers_reference" UNIQUE ("reference");

ALTER TABLE "lender_answers" ADD CONSTRAINT "uq_lender_answers_idempotency_key" UNIQUE ("idempotency_key");

CREATE INDEX "ix_api_keys_owner_id" ON "api_keys" ("owner_id");

ALTER TABLE "api_keys" ADD CONSTRAINT "uq_api_keys_key_hash" UNIQUE ("key_hash");

COMMENT ON TABLE "lender_answers" IS 'An answer the lender gave.';

COMMENT ON TABLE "api_keys" IS 'API keys the vendor issued. Only the SHA-256 hash of a key is stored.';
