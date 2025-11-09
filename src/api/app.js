/* eslint-disable quotes */
/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import chalk from 'chalk';
import cors from 'cors';
import fs from 'fs-extra';
import helmet from 'helmet';
import history from 'connect-history-api-fallback';
import morgan from 'morgan';
import multer from 'multer';
import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

import LoggerService from '../services/logger/logger.service.js';

import express from 'express';

//swagger
import swaggerJsdoc from 'swagger-jsdoc';
import swaggerUi from 'swagger-ui-express';
import swaggerOptions from './docs/swagger.js';

import * as AuthRouter from './components/auth/auth.routes.js';
import * as BackupRouter from './components/backup/backup.routes.js';
import * as CamerasRouter from './components/cameras/cameras.routes.js';
import * as ConfigRouter from './components/config/config.routes.js';
import * as FilesRouter from './components/files/files.routes.js';
import * as NotificationsRouter from './components/notifications/notifications.routes.js';
import * as RecordingsRouter from './components/recordings/recordings.routes.js';
import * as SettingsRouter from './components/settings/settings.routes.js';
import * as SubscribeRouter from './components/subscribe/subscribe.routes.js';
import * as SystemRouter from './components/system/system.routes.js';
import * as UsersRouter from './components/users/users.routes.js';
import * as SchedulesRouter from './components/schedules/schedules.routes.js';
import * as EventsRouter from './components/events/events.routes.js';
import EventAreaRouter from './components/eventArea/eventArea.routes.js';
import * as AlertsRouter from './components/alerts/alerts.routes.js';
import * as PanoramaRouter from './components/panorama/panorama.routes.js';
const { log } = LoggerService;

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
const specs = swaggerJsdoc(swaggerOptions);

export default class App {
  constructor(options) {
    // Initialize LoggerService
    new LoggerService({
      log: {
        prefix: 'camera.ui',
        info: console.info,
        warn: console.warn,
        error: console.error,
        debug: console.debug
      }
    });

    // Set environment variables for logging
    process.env.CUI_LOG_MODE = options.debug ? '2' : '1';  // 2 for debug, 1 for info
    process.env.CUI_LOG_COLOR = '1';  // Enable colored logs
    process.env.CUI_LOG_TIMESTAMPS = '1';  // Enable timestamps

    app.use(cors({
      origin: '*',
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      allowedHeaders: ['Content-Type', 'Authorization', 'Range', 'Accept', 'Cache-Control'],
      exposedHeaders: ['Content-Range', 'Accept-Ranges', 'Content-Length', 'Content-Type'],
      credentials: true,
      maxAge: 86400
    }));

    // Increase limits for large requests
    app.use(express.json({ limit: '100mb' }));
    app.use(express.urlencoded({ extended: true, limit: '100mb' }));

    // Increase header size limit
    app.set('max-http-header-size', 65536); // 64KB

    // Remove strict header checking
    app.set('strict routing', false);
    app.set('strict query parser', false);

    app.use(
      helmet({
        crossOriginEmbedderPolicy: false,
        crossOriginOpenerPolicy: false,
        crossOriginResourcePolicy: false,
        originAgentCluster: false,
      })
    );
    app.use(
      helmet.contentSecurityPolicy({
        useDefaults: false,
        directives: {
          defaultSrc: ["'unsafe-eval'", "'unsafe-inline'", "'self'"],
          scriptSrc: ["'unsafe-eval'", "'unsafe-inline'", "'self'", 'https://*.googleapis.com', 'blob:', 'data:'],
          childSrc: ["'unsafe-eval'", "'unsafe-inline'", "'self'", 'blob:', 'https:'],
          fontSrc: ["'unsafe-eval'", "'unsafe-inline'", "'self'", 'data:'],
          connectSrc: [
            'ws:',
            'wss:',
            'https:',
            'blob:',
            'data:',
            'file:',
            'filesystem:',
            'mediastream:',
            'https://registry.npmjs.org',
            'https://unpkg.com',
            "'unsafe-eval'",
            "'unsafe-inline'",
            "'self'",
          ],
          imgSrc: ["'unsafe-eval'", "'unsafe-inline'", "'self'", 'data:', 'blob:', 'https://openweathermap.org'],
          mediaSrc: ["'unsafe-eval'", "'unsafe-inline'", "'self'", 'data:', 'blob:'],
        },
      })
    );

    app.use(
      morgan(
        (tokens, req, res) => {
          // eslint-disable-next-line unicorn/consistent-function-scoping
          const headersSent = (res) => {
            return typeof res.headersSent !== 'boolean' ? Boolean(res._header) : res.headersSent;
          };

          const status = headersSent(res) ? res.statusCode : undefined;

          const color =
            status >= 500
              ? 'redBright'
              : status >= 400
                ? 'yellowBright'
                : status >= 300
                  ? 'cyanBright'
                  : status >= 200
                    ? 'greenBright'
                    : 'gray';

          return [
            chalk.gray(tokens.method(req, res)),
            chalk.gray(tokens.url(req, res)),
            chalk[color](tokens.status(req, res)),
            chalk.gray(tokens['response-time'](req, res)),
            chalk.gray('ms'),
            chalk.gray('-'),
            chalk.gray(tokens.res(req, res, 'content-length') || ''),
          ].join(' ');
        },
        {
          skip: () => !options.debug,
          stream: {
            write: (line) => {
              log.debug(line.replace(/^\s+|\s+$/g, ''));
            },
          },
        }
      )
    );

    const backupUpload = multer({
      storage: multer.diskStorage({
        destination: async (request, file, callback) => {
          const backupDirectory = await fs.mkdtemp(path.join(os.tmpdir(), 'cameraui-restore-'));
          callback(null, backupDirectory);
        },
        filename: (request, file, callback) => {
          callback(null, file.originalname);
        },
      }),
    });

    AuthRouter.routesConfig(app);
    BackupRouter.routesConfig(app, backupUpload);
    CamerasRouter.routesConfig(app);
    ConfigRouter.routesConfig(app);
    FilesRouter.routesConfig(app);
    NotificationsRouter.routesConfig(app);
    RecordingsRouter.routesConfig(app);
    SettingsRouter.routesConfig(app);
    SubscribeRouter.routesConfig(app);
    SystemRouter.routesConfig(app);
    UsersRouter.routesConfig(app);
    AlertsRouter.routesConfig(app);
    app.use('/api', EventsRouter.default || EventsRouter);
    app.use('/api', EventAreaRouter);
    PanoramaRouter.routesConfig(app);
    log.info('Registering schedules routes...', 'App');
    SchedulesRouter.routesConfig(app);
    log.info('Schedules routes registered', 'App');


    app.get('/version', (req, res) => {
      res.status(200).send({
        version: options.version,
      });
    });

    app.use(
      '/swagger',
      swaggerUi.serve,
      swaggerUi.setup(specs, {
        explorer: true,
        swaggerOptions: {
          displayRequestDuration: true,
          docExpansion: 'none',
          filter: false,
          showExtensions: true,
          showCommonExtensions: true,
          displayOperationId: false,
        },
      })
    );

    // SPA 라우팅을 위한 history API fallback 설정
    // API 경로(/api/*)와 특정 경로(/swagger, /version)를 제외하고 모든 GET 요청을 index.html로 리다이렉트
    app.use(history({
      index: '/index.html',
      // API 경로와 특정 경로를 제외
      rewrites: [
        // API 경로는 제외 (원래 경로 유지)
        { from: /^\/api\/.*$/, to: function (context) { return context.parsedUrl.pathname; } },
        // swagger 경로는 제외
        { from: /^\/swagger\/.*$/, to: function (context) { return context.parsedUrl.pathname; } },
        // version 경로는 제외
        { from: /^\/version$/, to: function (context) { return context.parsedUrl.pathname; } }
      ],
      // HTML Accept 헤더가 있는 요청만 처리
      htmlAcceptHeaders: ['text/html', 'application/xhtml+xml'],
      // 점이 있는 파일 경로도 처리
      disableDotRule: true
    }));
    app.use(express.static(path.join(__dirname, '../../interface')));

    return app;
  }
}
