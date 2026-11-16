DO $$ BEGIN CREATE TYPE "viewing_status" AS ENUM ('requested', 'confirmed', 'completed', 'cancelled', 'no_show'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "viewings" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "starts_at" TIMESTAMPTZ NOT NULL,
    "ends_at" TIMESTAMPTZ NOT NULL,
    "listing_title" VARCHAR(200) NOT NULL,
    "buyer_name" VARCHAR(200) NOT NULL,
    "status" "viewing_status" NOT NULL DEFAULT ('requested'),
    "agent_name" VARCHAR(200) NOT NULL,
    "note" VARCHAR(500),
    "listing_id" UUID NOT NULL,
    "buyer_email" VARCHAR(320) NOT NULL,
    "agent_email" VARCHAR(320) NOT NULL,
    "reminder_sent" BOOLEAN NOT NULL DEFAULT (FALSE),
    PRIMARY KEY ("id")
);

ALTER TABLE "viewings" ADD CONSTRAINT "chk_viewings_agent_name_b28b8d16" CHECK ((char_length("agent_name") <= 200));

ALTER TABLE "viewings" ADD CONSTRAINT "chk_viewings_buyer_name_20c2bccd" CHECK ((char_length("buyer_name") <= 200));

ALTER TABLE "viewings" ADD CONSTRAINT "chk_viewings_listing_title_3dd2881f" CHECK ((char_length("listing_title") <= 200));

ALTER TABLE "viewings" ADD CONSTRAINT "chk_viewings_note_db49f8ea" CHECK ((char_length("note") <= 500));

CREATE INDEX "ix_viewings_listing_id" ON "viewings" ("listing_id");

CREATE INDEX "ix_viewings_buyer_email" ON "viewings" ("buyer_email");

CREATE INDEX "ix_viewings_agent_email" ON "viewings" ("agent_email");
