CREATE TABLE IF NOT EXISTS recording_schedules (
  id INT AUTO_INCREMENT PRIMARY KEY,
  camera_name VARCHAR(255) NOT NULL,
  start_time TIME NOT NULL,
  end_time TIME NOT NULL,
  days JSON NOT NULL,
  recording_type ENUM('Video', 'Snapshot') NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_camera_name (camera_name),
  INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4; 