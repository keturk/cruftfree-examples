/**
 * Metrics for pubsub contract violations (auto-generated).
 *
 * Every transport directory of a service (each pub/sub block and the queue side) carries its own
 * copy of this module, and prom-client's default registry refuses a second counter of the same
 * name: the counter is looked up first, so the copies share the one the process registered.
 */
import * as client from 'prom-client';

const CONTRACT_VIOLATIONS_METRIC = 'contract_violations_total';

export const contractViolationCounter: client.Counter<'event' | 'clause'> =
  (client.register.getSingleMetric(CONTRACT_VIOLATIONS_METRIC) as client.Counter<'event' | 'clause'> | undefined) ??
  new client.Counter({
    name: CONTRACT_VIOLATIONS_METRIC,
    help: 'Number of event contract violations',
    labelNames: ['event', 'clause'],
  });
