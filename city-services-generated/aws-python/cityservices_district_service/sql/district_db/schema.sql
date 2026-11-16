DO $$ BEGIN CREATE TYPE "zoning_type" AS ENUM ('residential', 'commercial', 'industrial', 'mixed_use'); EXCEPTION WHEN duplicate_object OR unique_violation THEN null; END $$;

CREATE TABLE "districts" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "name" VARCHAR(200) NOT NULL,
    "code" VARCHAR(20) NOT NULL,
    "population" BIGINT NOT NULL DEFAULT (0),
    "boundary_geo_json" TEXT NOT NULL,
    "boundary" geometry(Geometry,4326),
    "description" TEXT,
    PRIMARY KEY ("id")
);

CREATE TABLE "zoning_areas" (
    "created_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "updated_at" TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP),
    "id" UUID NOT NULL DEFAULT (gen_random_uuid()),
    "name" VARCHAR(200) NOT NULL,
    "zone_code" VARCHAR(20) NOT NULL,
    "type" "zoning_type" NOT NULL,
    "boundary_geo_json" TEXT NOT NULL,
    "boundary" geometry(Geometry,4326),
    "district_id" UUID NOT NULL,
    PRIMARY KEY ("id")
);

ALTER TABLE "zoning_areas" ADD CONSTRAINT "fk_zoning_areas_district_id" FOREIGN KEY ("district_id") REFERENCES "districts" ("id") ON DELETE RESTRICT ON UPDATE RESTRICT;

ALTER TABLE "districts" ADD CONSTRAINT "chk_districts_code_767438d9" CHECK ((char_length("code") <= 20));

ALTER TABLE "districts" ADD CONSTRAINT "chk_districts_name_f39d5e94" CHECK ((char_length("name") <= 200));

ALTER TABLE "districts" ADD CONSTRAINT "chk_districts_population_6fa1c152" CHECK (("population" >= 0));

ALTER TABLE "zoning_areas" ADD CONSTRAINT "chk_zoning_areas_name_f39d5e94" CHECK ((char_length("name") <= 200));

ALTER TABLE "zoning_areas" ADD CONSTRAINT "chk_zoning_areas_zone_code_4f7ea0c9" CHECK ((char_length("zone_code") <= 20));

CREATE INDEX "gist_districts_boundary" ON "districts" USING GIST ("boundary");

ALTER TABLE "districts" ADD CONSTRAINT "uq_districts_code" UNIQUE ("code");

CREATE INDEX "ix_zoning_areas_district_id" ON "zoning_areas" ("district_id");

CREATE INDEX "gist_zoning_areas_boundary" ON "zoning_areas" USING GIST ("boundary");

ALTER TABLE "zoning_areas" ADD CONSTRAINT "uq_zoning_areas_zone_code" UNIQUE ("zone_code");
