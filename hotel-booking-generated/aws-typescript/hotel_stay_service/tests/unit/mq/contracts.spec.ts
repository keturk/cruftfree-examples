/**
 * Tests for event contract validation (auto-generated).
 */
import { validateStayConfirmedContract, validateStayCancelledContract, validateHoldLapsedContract, validateArrivingTomorrowContract, validateGuestLeftContract } from '../../../src/mq/contracts';
import { ContractViolationError } from '../../../src/errors/contract-violation';

describe('StayConfirmed contracts', () => {
  it("pubsub_contract/mq/StayConfirmed/accepts_valid_payload", () => {
    expect(() =>
      validateStayConfirmedContract(
        'aaaa',
        'test',
        'test',
        'test',
        'test',
        'test',
        'test',
      ),
    ).not.toThrow();
  });

  it("pubsub_contract/mq/StayConfirmed/0/rejects_violated_clause", () => {
    expect(() =>
      validateStayConfirmedContract(
        '',
        'test',
        'test',
        'test',
        'test',
        'test',
        'test',
      ),
    ).toThrow(ContractViolationError);
  });

});

describe('StayCancelled contracts', () => {
  it("pubsub_contract/mq/StayCancelled/accepts_valid_payload", () => {
    expect(() =>
      validateStayCancelledContract(
        'aaaa',
        'test',
        'test',
      ),
    ).not.toThrow();
  });

  it("pubsub_contract/mq/StayCancelled/0/rejects_violated_clause", () => {
    expect(() =>
      validateStayCancelledContract(
        '',
        'test',
        'test',
      ),
    ).toThrow(ContractViolationError);
  });

});

describe('HoldLapsed contracts', () => {
  it("pubsub_contract/mq/HoldLapsed/accepts_valid_payload", () => {
    expect(() =>
      validateHoldLapsedContract(
        'aaaa',
        'test',
        'test',
      ),
    ).not.toThrow();
  });

  it("pubsub_contract/mq/HoldLapsed/0/rejects_violated_clause", () => {
    expect(() =>
      validateHoldLapsedContract(
        '',
        'test',
        'test',
      ),
    ).toThrow(ContractViolationError);
  });

});

describe('ArrivingTomorrow contracts', () => {
  it("pubsub_contract/mq/ArrivingTomorrow/accepts_valid_payload", () => {
    expect(() =>
      validateArrivingTomorrowContract(
        'aaaa',
        'test',
        'test',
        'test',
      ),
    ).not.toThrow();
  });

  it("pubsub_contract/mq/ArrivingTomorrow/0/rejects_violated_clause", () => {
    expect(() =>
      validateArrivingTomorrowContract(
        '',
        'test',
        'test',
        'test',
      ),
    ).toThrow(ContractViolationError);
  });

});

describe('GuestLeft contracts', () => {
  it("pubsub_contract/mq/GuestLeft/accepts_valid_payload", () => {
    expect(() =>
      validateGuestLeftContract(
        'aaaa',
        'test',
        'test',
      ),
    ).not.toThrow();
  });

  it("pubsub_contract/mq/GuestLeft/0/rejects_violated_clause", () => {
    expect(() =>
      validateGuestLeftContract(
        '',
        'test',
        'test',
      ),
    ).toThrow(ContractViolationError);
  });

});

