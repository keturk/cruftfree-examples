import { Test, TestingModule } from '@nestjs/testing';
import { INestApplication } from '@nestjs/common';
import request from 'supertest';
import { AppModule } from '../../../src/app.module';

describe('RoomTypeController Integration', () => {
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

  it('should create and retrieve a roomType', async () => {
    const createDto = {
      createdAt: new Date(),
      updatedAt: new Date(),
      name: 'test_value',
      summary: 'test_value',
      description: "test_value",
      sleeps: 1,
      nightlyRate: '19.99',
      inventory: 1,
      listed: true,
    };

    const createResponse = await request(app.getHttpServer())
      .post('/api/v1/desk/room-types')
      .set('Authorization', 'Bearer test-token')
      .send(createDto)
      .expect(201);

    const id = createResponse.body.id;

    const getResponse = await request(app.getHttpServer())
      .get(`/api/v1/desk/room-types/${id}`)
      .set('Authorization', 'Bearer test-token')
      .expect(200);

    expect(getResponse.body.id).toBe(id);
  });

  it('should create and update a roomType', async () => {
    const createDto = {
      createdAt: new Date(),
      updatedAt: new Date(),
      name: 'test_value',
      summary: 'test_value',
      description: "test_value",
      sleeps: 1,
      nightlyRate: '19.99',
      inventory: 1,
      listed: true,
    };

    const createResponse = await request(app.getHttpServer())
      .post('/api/v1/desk/room-types')
      .set('Authorization', 'Bearer test-token')
      .send(createDto)
      .expect(201);

    const id = createResponse.body.id;

    const updateDto = {
      createdAt: new Date(),
      updatedAt: new Date(),
      name: 'test_value',
      summary: 'test_value',
      description: "test_value",
      sleeps: 1,
      nightlyRate: '19.99',
      inventory: 1,
      listed: true,
    };

    await request(app.getHttpServer())
      .put(`/api/v1/desk/room-types/${id}`)
      .set('Authorization', 'Bearer test-token')
      .send(updateDto)
      .expect(200);
  });

  it('should create and delete a roomType', async () => {
    const createDto = {
      createdAt: new Date(),
      updatedAt: new Date(),
      name: 'test_value',
      summary: 'test_value',
      description: "test_value",
      sleeps: 1,
      nightlyRate: '19.99',
      inventory: 1,
      listed: true,
    };

    const createResponse = await request(app.getHttpServer())
      .post('/api/v1/desk/room-types')
      .set('Authorization', 'Bearer test-token')
      .send(createDto)
      .expect(201);

    const id = createResponse.body.id;

    await request(app.getHttpServer())
      .delete(`/api/v1/desk/room-types/${id}`)
      .set('Authorization', 'Bearer test-token')
      .expect(204);
  });

});
