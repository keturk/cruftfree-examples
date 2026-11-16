import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('ChannelApi Custom Endpoints', () => {
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

  describe('POST /v1/availability?request=integration-path-value', () => {
    it('should handle postAvailability request', async () => {
      const response = await request(app.getHttpServer())
        .post('/v1/availability?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

});
