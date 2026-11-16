import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('HomesApi Custom Endpoints', () => {
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

  describe('GET /api/v1/homes/', () => {
    it('should handle getEndpoint request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/homes/')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/homes/search?q=test', () => {
    it('should handle getSearch request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/homes/search?q=test')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/homes/pins', () => {
    it('should handle getPins request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/homes/pins')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/homes/home/00000000-0000-0000-0000-000000000001', () => {
    it('should handle getHomeById request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/homes/home/00000000-0000-0000-0000-000000000001')
        ;
      expect([200, 404]).toContain(response.status);
    });
  });

});
