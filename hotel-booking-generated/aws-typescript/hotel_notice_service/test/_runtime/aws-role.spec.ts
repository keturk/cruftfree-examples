/**
 * Jest spec of the AWS role runtime module (`src/_runtime/aws-role.ts`).
 *
 * The chain runs over in-memory providers of the shape the SDK's providers return: one that
 * answers and one that refuses. A client class records the configuration it was built with.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import { awsAssumedRoleClient, awsClient, roleProviderChain } from '../../src/_runtime/aws-role';
import type { AwsRoleIdentity, AwsRoleProvider } from '../../src/_runtime/aws-role';

const ROLE: AwsRoleIdentity = { accessKeyId: 'ASIAROLE', secretAccessKey: 'role-secret', sessionToken: 'token' };
const REGION = 'eu-west-1';

const answers: AwsRoleProvider = async () => ROLE;
const refuses: AwsRoleProvider = async () => {
  throw new Error('no container endpoint');
};

class RecordingClient {
  constructor(readonly config: { readonly region: string; readonly credentials: AwsRoleProvider }) {}
}

describe('roleProviderChain', () => {
  it('returns the first credential a source yields', async () => {
    await expect(roleProviderChain('metadata', [refuses, answers])()).resolves.toBe(ROLE);
  });

  it('fails closed when no source yields one, naming the channel and each refusal', async () => {
    await expect(roleProviderChain('lambda-runtime', [refuses])()).rejects.toThrow(
      /No AWS role credential on the 'lambda-runtime' channel \(no container endpoint\)/,
    );
  });
});

describe('awsClient', () => {
  it('keeps the configuration and resolves the role when the client first signs', () => {
    const client = awsClient(RecordingClient, { region: REGION });

    expect(client.config.region).toBe(REGION);
    expect(typeof client.config.credentials).toBe('function');
  });

  it('replaces any credential the configuration carries with the role', () => {
    const client = awsClient(RecordingClient, { region: REGION, credentials: answers });

    expect(client.config.credentials).not.toBe(answers);
  });
});

describe('awsAssumedRoleClient', () => {
  it('signs with the assumed role it is handed', () => {
    const client = awsAssumedRoleClient(RecordingClient, { region: REGION }, answers);

    expect(client.config.credentials).toBe(answers);
  });
});
