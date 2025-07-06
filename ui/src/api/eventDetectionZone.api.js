import api from './index';

const resource = '/detectionZone';

export const getEventDetectionZone = () => api.get(resource);
export const getEventDetectionZoneById = (id) => api.get(`${resource}/${id}`);
export const addEventDetectionZone = (eventDetectionZone) => api.post(resource, eventDetectionZone);
export const updateEventDetectionZone = (id, eventDetectionZone) => api.put(`${resource}/${id}`, eventDetectionZone);
export const deleteEventDetectionZone = (id) => api.delete(`${resource}/${id}`);
export const updateInPageZone = (inPageZone) => api.put('/detectionZone/inPageZone', { in_page_zone: inPageZone }); 
