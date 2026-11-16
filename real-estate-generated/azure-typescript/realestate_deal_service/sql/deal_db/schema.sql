DO $$ BEGIN CREATE TYPE "contract_status" AS ENUM ('awaiting_signature', 'signed', 'declined'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "financing" AS ENUM ('cash', 'mortgage'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "offer_status" AS ENUM ('submitted', 'accepted', 'rejected', 'withdrawn'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "offers" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "listing_title" VARCHAR(200) NOT NULL,
    "buyer_name" VARCHAR(200) NOT NULL,
    "amount" DECIMAL(19,4) NOT NULL,
    "financing" "financing" NOT NULL,
    "status" "offer_status" NOT NULL DEFAULT ('submitted'),
    "lender_reference" VARCHAR(40),
    "listing_id" UUID NOT NULL,
    "buyer_email" VARCHAR(320) NOT NULL,
    "agent_email" VARCHAR(320) NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "contracts" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "listing_title" VARCHAR(200) NOT NULL,
    "buyer_name" VARCHAR(200) NOT NULL,
    "price" DECIMAL(19,4) NOT NULL,
    "status" "contract_status" NOT NULL DEFAULT ('awaiting_signature'),
    "signed_at" TIMESTAMPTZ,
    "envelope_id" VARCHAR(40),
    "listing_id" UUID NOT NULL,
    "offer_id" UUID NOT NULL,
    "buyer_email" VARCHAR(320) NOT NULL,
    "agent_email" VARCHAR(320) NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "offers" ADD CONSTRAINT "chk_offers_buyer_name_20c2bccd" CHECK ((char_length("buyer_name") <= 200));

ALTER TABLE "offers" ADD CONSTRAINT "chk_offers_lender_reference_d709ae72" CHECK ((char_length("lender_reference") <= 40));

ALTER TABLE "offers" ADD CONSTRAINT "chk_offers_listing_title_3dd2881f" CHECK ((char_length("listing_title") <= 200));

ALTER TABLE "contracts" ADD CONSTRAINT "chk_contracts_buyer_name_20c2bccd" CHECK ((char_length("buyer_name") <= 200));

ALTER TABLE "contracts" ADD CONSTRAINT "chk_contracts_envelope_id_f51afe7b" CHECK ((char_length("envelope_id") <= 40));

ALTER TABLE "contracts" ADD CONSTRAINT "chk_contracts_listing_title_3dd2881f" CHECK ((char_length("listing_title") <= 200));

CREATE INDEX "ix_offers_listing_id" ON "offers" ("listing_id");

CREATE INDEX "ix_offers_buyer_email" ON "offers" ("buyer_email");

CREATE INDEX "ix_offers_agent_email" ON "offers" ("agent_email");

CREATE INDEX "ix_contracts_buyer_email" ON "contracts" ("buyer_email");

CREATE INDEX "ix_contracts_agent_email" ON "contracts" ("agent_email");

ALTER TABLE "contracts" ADD CONSTRAINT "uq_contracts_listing_id" UNIQUE ("listing_id");

COMMENT ON COLUMN "contracts"."listing_id" IS 'One home, one contract: the unique key is what the database itself refuses to break.';
