import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('AgentDealApi Custom Endpoints', () => {
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

  describe('GET /api/v1/agent/deals/summary', () => {
    it('should handle getSummary request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/agent/deals/summary')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('POST /api/v1/agent/deals/accept/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postAcceptById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/agent/deals/accept/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/agent/deals/reject/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postRejectById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/agent/deals/reject/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

});
