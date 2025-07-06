import Database from '../../database.js';
import lodash from 'lodash';
import { v4 as uuidv4 } from 'uuid';

const getAllEventAreas = async () => {
  await Database.interfaceDB.read();
  return Database.interfaceDB.data.eventArea || [];
};

const getEventAreaById = async (id) => {
  await Database.interfaceDB.read();
  return (Database.interfaceDB.data.eventArea || []).find(e => e.id === id) || null;
};

const addEventArea = async (eventArea) => {
  await Database.interfaceDB.read();
  if (!Database.interfaceDB.data.eventArea) Database.interfaceDB.data.eventArea = [];
  eventArea.id = uuidv4();
  Database.interfaceDB.data.eventArea.push(eventArea);
  await Database.interfaceDB.write();
  return eventArea;
};

const updateEventArea = async (id, update) => {
  await Database.interfaceDB.read();
  const idx = (Database.interfaceDB.data.eventArea || []).findIndex(e => e.id === id);
  if (idx === -1) return null;
  Database.interfaceDB.data.eventArea[idx] = {
    ...Database.interfaceDB.data.eventArea[idx],
    ...update,
    id // id는 변경 불가
  };
  await Database.interfaceDB.write();
  return Database.interfaceDB.data.eventArea[idx];
};

const deleteEventArea = async (id) => {
  await Database.interfaceDB.read();
  const before = Database.interfaceDB.data.eventArea.length;
  Database.interfaceDB.data.eventArea = (Database.interfaceDB.data.eventArea || []).filter(e => e.id !== id);
  await Database.interfaceDB.write();
  return Database.interfaceDB.data.eventArea.length < before;
};

export {
  getAllEventAreas,
  getEventAreaById,
  addEventArea,
  updateEventArea,
  deleteEventArea
}; 