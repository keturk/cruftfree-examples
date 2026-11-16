import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('DeskApi Custom Endpoints', () => {
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

  describe('GET /api/v1/desk/today', () => {
    it('should handle getToday request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/today')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/desk/arrivals', () => {
    it('should handle getArrivals request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/arrivals')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/desk/departures', () => {
    it('should handle getDepartures request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/departures')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/desk/occupancy', () => {
    it('should handle getOccupancy request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/occupancy')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/desk/calendar', () => {
    it('should handle getCalendar request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/calendar')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('GET /api/v1/desk/stays/00000000-0000-0000-0000-000000000001', () => {
    it('should handle getStaysById request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/stays/00000000-0000-0000-0000-000000000001')
        .set('Authorization', 'Bearer test-token')
        ;
      expect([200, 404]).toContain(response.status);
    });
  });

  describe('GET /api/v1/desk/stays/00000000-0000-0000-0000-000000000001/free-rooms', () => {
    it('should handle getStaysByIdFreeRooms request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/stays/00000000-0000-0000-0000-000000000001/free-rooms')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('POST /api/v1/desk/check-in?request=integration-path-value', () => {
    it('should handle postCheckIn request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/check-in?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('POST /api/v1/desk/stays/00000000-0000-0000-0000-000000000001/check-out', () => {
    it('should handle postStaysByIdCheckOut request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/stays/00000000-0000-0000-0000-000000000001/check-out')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/desk/stays/00000000-0000-0000-0000-000000000001/cancel', () => {
    it('should handle postStaysByIdCancel request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/stays/00000000-0000-0000-0000-000000000001/cancel')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

  describe('POST /api/v1/desk/note?request=integration-path-value', () => {
    it('should handle postNote request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/note?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect(response.status).toBe(201);
    });
  });

  describe('GET /api/v1/desk/rooms', () => {
    it('should handle getRooms request', async () => {
      const response = await request(app.getHttpServer())
        .get('/api/v1/desk/rooms')
        .set('Authorization', 'Bearer test-token')
        ;
      expect(response.status).toBe(200);
    });
  });

  describe('POST /api/v1/desk/rooms/00000000-0000-0000-0000-000000000001/condition?request=integration-path-value', () => {
    it('should handle postRoomsByIdCondition request', async () => {
      const response = await request(app.getHttpServer())
        .post('/api/v1/desk/rooms/00000000-0000-0000-0000-000000000001/condition?request=integration-path-value')
        .set('Authorization', 'Bearer test-token')
        .send({});
      expect([201, 404]).toContain(response.status);
    });
  });

});
