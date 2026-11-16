DO $$ BEGIN CREATE TYPE "facility_type" AS ENUM ('library', 'fire_station', 'community_center', 'clinic'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "facilities" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "name" VARCHAR(200) NOT NULL,
    "type" "facility_type" NOT NULL,
    "latitude" DOUBLE PRECISION NOT NULL,
    "longitude" DOUBLE PRECISION NOT NULL,
    "location" geometry(Geometry,4326),
    "address" VARCHAR(300) NOT NULL,
    "phone" VARCHAR(20) NOT NULL,
    "is_operational" BOOLEAN NOT NULL DEFAULT (TRUE),
    PRIMARY KEY ("id")
);

CREATE TABLE "parks" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "name" VARCHAR(200) NOT NULL,
    "boundary_geo_json" TEXT NOT NULL,
    "boundary" geometry(Geometry,4326),
    "is_open" BOOLEAN NOT NULL DEFAULT (TRUE),
    "amenities" TEXT,
    PRIMARY KEY ("id")
);

ALTER TABLE "facilities" ADD CONSTRAINT "chk_facilities_address_c06df1d3" CHECK ((char_length("address") <= 300));

ALTER TABLE "facilities" ADD CONSTRAINT "chk_facilities_name_f39d5e94" CHECK ((char_length("name") <= 200));

ALTER TABLE "parks" ADD CONSTRAINT "chk_parks_name_f39d5e94" CHECK ((char_length("name") <= 200));

CREATE INDEX "gist_facilities_location" ON "facilities" USING GIST ("location");

CREATE INDEX "gist_parks_boundary" ON "parks" USING GIST ("boundary");
