'use strict';

/**
 * Validates schedule data
 * @param {Object} scheduleData - The schedule data to validate
 * @returns {string|null} Error message if validation fails, null if validation passes
 */
const validateSchedule = (scheduleData) => {
  const { cameraName, days_of_week, start_time, end_time } = scheduleData;

  // Check required fields
  if (!cameraName) {
    return 'Camera name is required';
  }

  if (!Array.isArray(days_of_week) || days_of_week.length === 0) {
    return 'At least one day of week must be selected';
  }

  // Validate days of week values (0-6, where 0 is Sunday)
  const validDays = days_of_week.every(day => Number.isInteger(day) && day >= 0 && day <= 6);
  if (!validDays) {
    return 'Invalid day of week value. Must be between 0 and 6';
  }

  // Validate time format (HH:mm)
  const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
  if (!timeRegex.test(start_time)) {
    return 'Invalid start time format. Must be HH:mm';
  }
  if (!timeRegex.test(end_time)) {
    return 'Invalid end time format. Must be HH:mm';
  }

  // Compare start and end times
  const [startHour, startMinute] = start_time.split(':').map(Number);
  const [endHour, endMinute] = end_time.split(':').map(Number);
  const startMinutes = startHour * 60 + startMinute;
  const endMinutes = endHour * 60 + endMinute;

  if (startMinutes >= endMinutes) {
    return 'End time must be after start time';
  }

  return null;
};

export { validateSchedule }; 