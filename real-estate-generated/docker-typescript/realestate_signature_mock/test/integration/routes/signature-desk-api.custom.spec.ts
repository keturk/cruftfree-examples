import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('SignatureDeskApi Custom Endpoints', () => {
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

  describe('POST /api/v1/desk/signature/sign/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postSignById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/signature/sign/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/desk/signature/decline/00000000-0000-0000-0000-000000000001', () => {
    it('should handle postDeclineById request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/signature/decline/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

});
