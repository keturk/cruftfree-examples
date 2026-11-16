/** Jest configuration for hotel.EmailMock */

export default {
  preset: 'ts-jest',
  testEnvironment: 'node',
  setupFiles: ['reflect-metadata'],
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testMatch: ['**/*.spec.ts', '**/*.test.ts'],
  testPathIgnorePatterns: [
    '/node_modules/',
    '/dist/',
    '/test/integration/', // Integration tests run under jest-integration.config.ts
    '/test/spec/', // Spec tests run as deploy tests, not unit tests
  ],
  transform: {
    '^.+\\.ts$': ['ts-jest', { isolatedModules: true }],
  },
  workerIdleMemoryLimit: '512MB',
};
