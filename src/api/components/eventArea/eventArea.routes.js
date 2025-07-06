'use strict';

import * as EventAreaController from './eventArea.controller.js';
import LoggerService from '../../../services/logger/logger.service.js';
import express from 'express';

const router = express.Router();
const { log } = LoggerService;

// eventArea CRUD
router.get('/eventArea', EventAreaController.getAllEventAreas);
router.get('/eventArea/:id', EventAreaController.getEventAreaById);
router.post('/eventArea', EventAreaController.addEventArea);
router.put('/eventArea/:id', EventAreaController.updateEventArea);
router.delete('/eventArea/:id', EventAreaController.deleteEventArea);

export default router; 