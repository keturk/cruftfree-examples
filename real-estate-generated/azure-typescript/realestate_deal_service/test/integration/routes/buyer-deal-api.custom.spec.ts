import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('BuyerDealApi Custom Endpoints', () => {
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

  describe('GET /api/v1/offers/mine', () => {
    it('should handle getMine request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/offers/mine')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/offers/my-contracts', () => {
    it('should handle getMyContracts request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/offers/my-contracts')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('POST /api/v1/offers/make?request=integration-path-value', () => {
    it('should handle postMake request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/offers/make?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('POST /api/v1/offers/withdraw/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postWithdrawById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/offers/withdraw/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

});
