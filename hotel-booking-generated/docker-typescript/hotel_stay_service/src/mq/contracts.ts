/**
 * Event contract validation (auto-generated).
 */
import { ContractViolationError } from '../errors/contract-violation';
import { contractViolationCounter } from './contract-metrics';

export function validateStayConfirmedContract(
  code: string,
  guestName: string,
  guestEmail: string,
  roomTypeName: string,
  arrival: string,
  departure: string,
  total: string,
): void {
  if (!((((value: Iterable<unknown>): number => Array.from(value).length)(code) > 0))) {
    console.error('contract_violation', {
      event: 'StayConfirmed',
      clause: 'code.length > 0',
      code,
    });
    contractViolationCounter.inc({
      event: 'StayConfirmed',
      clause: 'code.length > 0',
    });
    throw new ContractViolationError({
      event: 'StayConfirmed',
      clause: 'code.length > 0',
      actual: {
        code,
      },
    });
  }
}

export function validateStayCancelledContract(
  code: string,
  guestEmail: string,
  roomTypeName: string,
): void {
  if (!((((value: Iterable<unknown>): number => Array.from(value).length)(code) > 0))) {
    console.error('contract_violation', {
      event: 'StayCancelled',
      clause: 'code.length > 0',
      code,
    });
    contractViolationCounter.inc({
      event: 'StayCancelled',
      clause: 'code.length > 0',
    });
    throw new ContractViolationError({
      event: 'StayCancelled',
      clause: 'code.length > 0',
      actual: {
        code,
      },
    });
  }
}

export function validateHoldLapsedContract(
  code: string,
  guestEmail: string,
  roomTypeName: string,
): void {
  if (!((((value: Iterable<unknown>): number => Array.from(value).length)(code) > 0))) {
    console.error('contract_violation', {
      event: 'HoldLapsed',
      clause: 'code.length > 0',
      code,
    });
    contractViolationCounter.inc({
      event: 'HoldLapsed',
      clause: 'code.length > 0',
    });
    throw new ContractViolationError({
      event: 'HoldLapsed',
      clause: 'code.length > 0',
      actual: {
        code,
      },
    });
  }
}

export function validateArrivingTomorrowContract(
  code: string,
  guestName: string,
  guestEmail: string,
  roomTypeName: string,
): void {
  if (!((((value: Iterable<unknown>): number => Array.from(value).length)(code) > 0))) {
    console.error('contract_violation', {
      event: 'ArrivingTomorrow',
      clause: 'code.length > 0',
      code,
    });
    contractViolationCounter.inc({
      event: 'ArrivingTomorrow',
      clause: 'code.length > 0',
    });
    throw new ContractViolationError({
      event: 'ArrivingTomorrow',
      clause: 'code.length > 0',
      actual: {
        code,
      },
    });
  }
}

export function validateGuestLeftContract(
  code: string,
  guestName: string,
  guestEmail: string,
): void {
  if (!((((value: Iterable<unknown>): number => Array.from(value).length)(code) > 0))) {
    console.error('contract_violation', {
      event: 'GuestLeft',
      clause: 'code.length > 0',
      code,
    });
    contractViolationCounter.inc({
      event: 'GuestLeft',
      clause: 'code.length > 0',
    });
    throw new ContractViolationError({
      event: 'GuestLeft',
      clause: 'code.length > 0',
      actual: {
        code,
      },
    });
  }
}

