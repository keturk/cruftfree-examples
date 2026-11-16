DO $$ BEGIN CREATE TYPE "listing_status" AS ENUM ('draft', 'active', 'under_offer', 'sold', 'withdrawn'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

DO $$ BEGIN CREATE TYPE "property_kind" AS ENUM ('house', 'apartment', 'townhouse', 'cottage', 'land'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "neighbourhoods" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "name" VARCHAR(120) NOT NULL,
    "city" VARCHAR(120) NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "listings" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "title" VARCHAR(200) NOT NULL,
    "neighbourhood_name" VARCHAR(120) NOT NULL,
    "kind" "property_kind" NOT NULL,
    "price" DECIMAL(19,4) NOT NULL,
    "bedrooms" BIGINT NOT NULL,
    "bathrooms" BIGINT NOT NULL,
    "area_sqm" BIGINT NOT NULL,
    "status" "listing_status" NOT NULL DEFAULT ('draft'),
    "agent_name" VARCHAR(200) NOT NULL,
    "published_at" TIMESTAMPTZ,
    "summary" TEXT NOT NULL,
    "city" VARCHAR(120) NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "agent_email" VARCHAR(320) NOT NULL,
    PRIMARY KEY ("id")
);

CREATE TABLE "price_changes" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "listing_id" UUID NOT NULL,
    "old_price" DECIMAL(19,4) NOT NULL,
    "new_price" DECIMAL(19,4) NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "neighbourhoods" ADD CONSTRAINT "chk_neighbourhoods_city_c037c334" CHECK ((char_length("city") <= 120));

ALTER TABLE "neighbourhoods" ADD CONSTRAINT "chk_neighbourhoods_name_f61d31a0" CHECK ((char_length("name") <= 120));

ALTER TABLE "listings" ADD CONSTRAINT "chk_listings_agent_name_b28b8d16" CHECK ((char_length("agent_name") <= 200));

ALTER TABLE "listings" ADD CONSTRAINT "chk_listings_city_c037c334" CHECK ((char_length("city") <= 120));

ALTER TABLE "listings" ADD CONSTRAINT "chk_listings_neighbourhood_name_40d053bf" CHECK ((char_length("neighbourhood_name") <= 120));

ALTER TABLE "listings" ADD CONSTRAINT "chk_listings_title_fa0e1671" CHECK ((char_length("title") <= 200));

ALTER TABLE "neighbourhoods" ADD CONSTRAINT "uq_neighbourhoods_name" UNIQUE ("name");

CREATE INDEX "ix_listings_fulltext" ON "listings" USING GIN (to_tsvector('english', coalesce("title", '') || ' ' || coalesce("summary", '') || ' ' || coalesce("neighbourhood_name", '')));

CREATE INDEX "ix_listings_status" ON "listings" ("status");

CREATE INDEX "ix_listings_agent_email" ON "listings" ("agent_email");

CREATE INDEX "ix_price_changes_listing_id" ON "price_changes" ("listing_id");

COMMENT ON TABLE "neighbourhoods" IS 'A neighbourhood the agency works in. Choosing one places a home on the map.';

COMMENT ON TABLE "price_changes" IS 'Every price a home has asked. Never changed once written.';

CREATE FUNCTION "trg_price_changes_append_only_7f0f83c3"() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF TG_OP = 'UPDATE' THEN IF (to_jsonb(NEW) - CAST(ARRAY['updated_at'] AS text[])) = (to_jsonb(OLD) - CAST(ARRAY['updated_at'] AS text[])) THEN RETURN NEW; END IF; END IF; RAISE EXCEPTION USING MESSAGE = 'table ' || TG_TABLE_NAME || ' is append-only: ' || TG_OP || ' is refused', ERRCODE = 'restrict_violation'; END $$;

CREATE TRIGGER "trg_price_changes_append_only_7f0f83c3" BEFORE UPDATE OR DELETE ON "price_changes" FOR EACH ROW EXECUTE FUNCTION "trg_price_changes_append_only_7f0f83c3"();

CREATE TRIGGER "trg_price_changes_append_only_7f0f83c3_truncate" BEFORE TRUNCATE ON "price_changes" FOR EACH STATEMENT EXECUTE FUNCTION "trg_price_changes_append_only_7f0f83c3"();
