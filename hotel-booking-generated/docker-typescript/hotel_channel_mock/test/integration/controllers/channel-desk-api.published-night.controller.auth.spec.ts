import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('PublishedNightController Auth', () => {
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

  describe('GET /api/v1/desk/channel/published_nights (unauthenticated)', () => {
    it('should return 401 without auth token', async () => {
      await request(app.getHttpServer())
        .get('/api/v1/desk/channel/published_nights')
        .expect(401);
    });
  });

  describe('GET /api/v1/desk/channel/published_nights (wrong role)', () => {
    it('should return 403 with wrong role', async () => {
      await request(app.getHttpServer())
        .get('/api/v1/desk/channel/published_nights')
        .set('Authorization', 'Bearer wrong-role-token')
        .expect(403);
    });
  });

});
