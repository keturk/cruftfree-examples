/**
 * AWS role credentials -- the one credential source a generated AWS SDK client signs with.
 *
 * The SDK's default chain reads static keys from the environment and shared files before the
 * role, so a stray key would silently replace the least-privilege role. Every client is built
 * here instead, from the channel the platform delivers the role through:
 *   metadata: the container credentials endpoint (an ECS or App Runner task role), then the
 *     instance metadata endpoint (an EC2 instance role);
 *   lambda-runtime: the execution role in the runtime's reserved variables, which no function
 *     configuration can set. Only a Lambda entry point binds this channel.
 *
 * A channel that yields nothing fails closed, naming what to attach. The credential is resolved
 * when a client first signs, so an entry point binds its channel after modules load.
 *
 * Shipped by cruftfree-codegen-typescript-core and emitted verbatim. Do not edit manually.
 */
import {
  fromContainerMetadata,
  fromEnv,
  fromInstanceMetadata,
} from '@aws-sdk/credential-providers';

/** A channel the AWS platform delivers a process's role through. */
export type AwsRoleChannel = 'metadata' | 'lambda-runtime';

/** The role's temporary credential, as the SDK signs with it. */
export interface AwsRoleIdentity {
  readonly accessKeyId: string;
  readonly secretAccessKey: string;
  readonly sessionToken?: string;
  readonly expiration?: Date;
}

/** Resolves the role's temporary credential. */
export type AwsRoleProvider = () => Promise<AwsRoleIdentity>;

/** The providers of each channel, in the order they are tried. */
const CHANNEL_SOURCES: Readonly<Record<AwsRoleChannel, () => readonly AwsRoleProvider[]>> = {
  metadata: () => [fromContainerMetadata(), fromInstanceMetadata()],
  'lambda-runtime': () => [fromEnv()],
};

let boundChannel: AwsRoleChannel = 'metadata';

/** Name the channel this process's role arrives through; every process reads metadata otherwise. */
export function bindAwsRoleChannel(channel: AwsRoleChannel): void {
  boundChannel = channel;
}

/** The first credential *sources* yields; none fails closed, naming *channel*. */
export function roleProviderChain(
  channel: AwsRoleChannel,
  sources: readonly AwsRoleProvider[],
): AwsRoleProvider {
  return async (): Promise<AwsRoleIdentity> => {
    const refusals: string[] = [];
    for (const source of sources) {
      try {
        return await source();
      } catch (refusal) {
        refusals.push(refusal instanceof Error ? refusal.message : String(refusal));
      }
    }
    throw new Error(
      `No AWS role credential on the '${channel}' channel (${refusals.join('; ')}). Expected the ` +
        'platform to deliver the service role; static keys from the environment or shared files ' +
        'are never used. Fix: attach the role to the task, instance or function this service runs as.',
    );
  };
}

/** The role credential of the channel bound when it is resolved. */
export function awsRoleCredentials(): AwsRoleProvider {
  return async (): Promise<AwsRoleIdentity> =>
    roleProviderChain(boundChannel, CHANNEL_SOURCES[boundChannel]())();
}

/** An SDK client class taking the configuration *awsClient* builds. */
export type AwsClientClass<Client, Config> = new (
  config: Config & { readonly credentials: AwsRoleProvider },
) => Client;

/** A client of *Client* in *config*, signed with the platform-delivered role alone. */
export function awsClient<Client, Config extends object>(
  Client: AwsClientClass<Client, Config>,
  config: Config,
): Client {
  return new Client({ ...config, credentials: awsRoleCredentials() });
}

/**
 * A client of *Client* signed with *credentials*: a role the service's own role assumed through
 * STS, for a grant the deployment confines to a role of its own.
 */
export function awsAssumedRoleClient<Client, Config extends object>(
  Client: AwsClientClass<Client, Config>,
  config: Config,
  credentials: AwsRoleProvider,
): Client {
  return new Client({ ...config, credentials });
}
