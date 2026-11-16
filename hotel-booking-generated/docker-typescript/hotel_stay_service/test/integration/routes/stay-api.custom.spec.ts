import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('StayApi Custom Endpoints', () => {
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

  describe('GET /api/v1/stays/room-types', () => {
    it('should handle getRoomTypes request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/stays/room-types')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/stays/room-types/00000000-0000-0000-0000-000000000001', () => {
    it('should handle getRoomTypesById request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/stays/room-types/00000000-0000-0000-0000-000000000001')
        ;
      expect([200, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/stays/search?request=integration-path-value', () => {
    it('should handle postSearch request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/stays/search?request=integration-path-value')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('POST /api/v1/stays/hold?request=integration-path-value', () => {
    it('should handle postHold request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/stays/hold?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('POST /api/v1/stays/pay?request=integration-path-value', () => {
    it('should handle postPay request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/stays/pay?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('GET /api/v1/stays/mine', () => {
    it('should handle getMine request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/stays/mine')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/stays/mine/00000000-0000-0000-0000-000000000001', () => {
    it('should handle getMineById request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/stays/mine/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        ;
      expect([200, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/stays/mine/00000000-0000-0000-0000-000000000001/cancel', () => {
    it('should handle postMineByIdCancel request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/stays/mine/00000000-0000-0000-0000-000000000001/cancel')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

});
