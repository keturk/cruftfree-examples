import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('ListingInternalApi Internal Endpoints', () => {
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

  describe('GET /internal/listings/facts/00000000-0000-0000-0000-000000000001 (internal)', () => {
    it('should handle internal getFactsById request', async () => {
      await request(app.getHttpServer())
        .get('/internal/listings/facts/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        .expect(404);
    });

    it('should reject external access to getFactsById', async () => {
      await request(app.getHttpServer())
        .get('/internal/listings/facts/00000000-0000-0000-0000-000000000001')
        .expect(401);
    });

    it('should reject a credential from a provider outside the route allow-list for getFactsById', async () => {
      await request(app.getHttpServer())
        .get('/internal/listings/facts/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer wrong-provider-token')
        .expect(403);
    });
  });

  describe('POST /internal/listings/under-offer?notice=integration-path-value (internal)', () => {
    it('should handle internal postUnderOffer request', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/under-offer?notice=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({})
        .expect(201);
    });

    it('should reject external access to postUnderOffer', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/under-offer?notice=integration-path-value')
        .expect(401);
    });

    it('should reject a credential from a provider outside the route allow-list for postUnderOffer', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/under-offer?notice=integration-path-value')
        .set('Authorization', 'Bearer wrong-provider-token')
        .expect(403);
    });
  });

  describe('POST /internal/listings/sold?notice=integration-path-value (internal)', () => {
    it('should handle internal postSold request', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/sold?notice=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({})
        .expect(201);
    });

    it('should reject external access to postSold', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/sold?notice=integration-path-value')
        .expect(401);
    });

    it('should reject a credential from a provider outside the route allow-list for postSold', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/sold?notice=integration-path-value')
        .set('Authorization', 'Bearer wrong-provider-token')
        .expect(403);
    });
  });

  describe('POST /internal/listings/reopen?notice=integration-path-value (internal)', () => {
    it('should handle internal postReopen request', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/reopen?notice=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({})
        .expect(201);
    });

    it('should reject external access to postReopen', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/reopen?notice=integration-path-value')
        .expect(401);
    });

    it('should reject a credential from a provider outside the route allow-list for postReopen', async () => {
      await request(app.getHttpServer())
        .post('/internal/listings/reopen?notice=integration-path-value')
        .set('Authorization', 'Bearer wrong-provider-token')
        .expect(403);
    });
  });

});
