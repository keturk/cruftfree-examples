/**
 * Tiles helpers for CruftFree ``Tiles.generate`` builtin.
 * Generates vector tiles from GeoJSON input via Tippecanoe.
 */

import { execFile } from 'child_process';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { promisify } from 'util';

const execFileAsync = promisify(execFile);

/** The Tippecanoe binary, which must be on PATH; no environment variable names another. */
const TIPPECANOE_BINARY = 'tippecanoe';

export async function _tilesGenerate(
  options: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const maxZoom = Number(options.maxZoom ?? 14);
  const minZoom = Number(options.minZoom ?? 0);

  const features: unknown[] = [];
  for (const [key, layer] of Object.entries(options)) {
    if (key === 'maxZoom' || key === 'minZoom') continue;
    if (Array.isArray(layer)) features.push(...layer);
  }

  const geojson = { type: 'FeatureCollection', features };

  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'tiles-'));
  try {
    const inputPath = path.join(tmpDir, 'input.geojson');
    const outputPath = path.join(tmpDir, 'output.mbtiles');
    fs.writeFileSync(inputPath, JSON.stringify(geojson));
    try {
      // Off the event loop: Tippecanoe runs for seconds to minutes on real GeoJSON.
      await execFileAsync(TIPPECANOE_BINARY, [
        '-o', outputPath,
        `-z${maxZoom}`,
        `-Z${minZoom}`,
        '--no-tile-compression',
        inputPath,
      ]);
    } catch (error: unknown) {
      if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
        throw new Error(
          `Tiles.generate requires Tippecanoe, which was not found as '${TIPPECANOE_BINARY}'. ` +
            'Install Tippecanoe (https://github.com/felt/tippecanoe) and ensure it is on PATH.',
        );
      }
      throw error;
    }
    const tileData = fs.readFileSync(outputPath);
    return { count: features.length, tiles: [], mbtiles: tileData };
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}
