import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('AgentListingApi Custom Endpoints', () => {
  let app: INestApplication;

  beforeAll(async () => {
    process.env.NODE_ENV = 'test';
    const moduleFixture: TestingModule = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    app = moduleFixture.createNestApplication();
    await app.init();
  });

  afterAll(async () => {
    await app.close();
  });

  describe('GET /api/v1/agent/listings/summary', () => {
    it('should handle getSummary request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/agent/listings/summary')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/agent/listings/page/00000000-0000-0000-0000-000000000001', () => {
    it('should handle getPageById request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/agent/listings/page/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        ;
      expect([200, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/agent/listings/new?request=integration-path-value', () => {
    it('should handle postNew request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/agent/listings/new?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('POST /api/v1/agent/listings/publish/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postPublishById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/agent/listings/publish/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/agent/listings/withdraw/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postWithdrawById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/agent/listings/withdraw/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/agent/listings/price?request=integration-path-value', () => {
    it('should handle postPrice request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/agent/listings/price?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

});
