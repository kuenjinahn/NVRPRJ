/* eslint-disable unicorn/prevent-abbreviations */
'use-strict';

import * as EventAreaModel from './eventArea.model.js';

export const getAllEventAreas = async (req, res) => {
  try {
    const data = await EventAreaModel.getAllEventAreas();
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const getEventAreaById = async (req, res) => {
  try {
    const data = await EventAreaModel.getEventAreaById(req.params.id);
    if (!data) return res.status(404).json({ error: 'Not found' });
    res.json(data);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const addEventArea = async (req, res) => {
  try {
    const eventArea = req.body;
    const result = await EventAreaModel.addEventArea(eventArea);
    res.status(201).json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const updateEventArea = async (req, res) => {
  try {
    const result = await EventAreaModel.updateEventArea(req.params.id, req.body);
    if (!result) return res.status(404).json({ error: 'Not found' });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};

export const deleteEventArea = async (req, res) => {
  try {
    const result = await EventAreaModel.deleteEventArea(req.params.id);
    if (!result) return res.status(404).json({ error: 'Not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}; 