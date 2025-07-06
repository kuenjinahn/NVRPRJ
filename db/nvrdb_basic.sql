-- --------------------------------------------------------
-- 호스트:                          localhost
-- 서버 버전:                        10.6.7-MariaDB - mariadb.org binary distribution
-- 서버 OS:                        Win64
-- HeidiSQL 버전:                  12.6.0.6765
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- nvrdb 데이터베이스 구조 내보내기
CREATE DATABASE IF NOT EXISTS `nvrdb` /*!40100 DEFAULT CHARACTER SET latin1 COLLATE latin1_general_ci */;
USE `nvrdb`;

-- 테이블 nvrdb.tb_access_history 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_access_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `userId` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `userName` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `token` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `ip_address` varchar(50) CHARACTER SET utf8mb4 NOT NULL,
  `access_type` int(11) NOT NULL,
  `login_time` datetime NOT NULL,
  `logout_time` datetime NOT NULL,
  `create_date` datetime NOT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

-- 테이블 데이터 nvrdb.tb_access_history:~0 rows (대략적) 내보내기

-- 테이블 nvrdb.tb_alert_history 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_alert_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fk_camera_id` int(11) NOT NULL DEFAULT 0,
  `alert_accur_time` datetime DEFAULT NULL,
  `alert_type` varchar(5) DEFAULT NULL,
  `alert_level` varchar(5) DEFAULT NULL,
  `alert_status` varchar(5) DEFAULT NULL,
  `alert_info_json` varchar(2048) DEFAULT NULL,
  `fk_detect_zone_id` int(11) DEFAULT 0,
  `fk_video_receive_data_id` int(11) DEFAULT 0,
  `fk_process_user_id` int(11) DEFAULT 0,
  `alert_process_time` datetime DEFAULT NULL,
  `alert_description` varchar(1024) DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_alert_history:~0 rows (대략적) 내보내기

-- 테이블 nvrdb.tb_alert_setting 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_alert_setting` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `alert_setting_json` varchar(2048) DEFAULT NULL,
  `fk_user_id` int(11) NOT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_alert_setting:~0 rows (대략적) 내보내기
INSERT INTO `tb_alert_setting` (`id`, `alert_setting_json`, `fk_user_id`, `create_date`, `update_date`) VALUES
	(2, '{"alert":{"enabled":true,"notificationType":"팝업","delay":5,"priority":"높음","repeatInterval":15,"useSound":true,"leakThreshold":5,"scenario":"scenario1"},"alarmLevels":{"scenario1":[20,60,70,80],"scenario2":[10,15,20,25],"scenario3":[2,3,4,5]},"notification":{"emailEnabled":false,"emailAddress":"","emailAlarmLevel":3,"smsEnabled":false,"phoneNumber":"","smsAlarmLevel":4}}', 1, '2025-05-25 07:30:06', '2025-06-19 05:19:45');

-- 테이블 nvrdb.tb_cameras 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_cameras` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `motionTimeout` int(11) DEFAULT 15,
  `recordOnMovement` tinyint(1) DEFAULT 0,
  `prebuffering` tinyint(1) DEFAULT 0,
  `videoConfig` longtext CHARACTER SET utf8mb4 NOT NULL,
  `mqtt` longtext CHARACTER SET utf8mb4 DEFAULT NULL,
  `smtp` longtext CHARACTER SET utf8mb4 DEFAULT NULL,
  `videoanalysis` longtext CHARACTER SET utf8mb4 DEFAULT NULL,
  `settings` longtext CHARACTER SET utf8mb4 DEFAULT NULL,
  `prebufferLength` int(11) DEFAULT 4,
  `create_date` datetime NOT NULL,
  `update_dt` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

-- 테이블 데이터 nvrdb.tb_cameras:~2 rows (대략적) 내보내기
INSERT INTO `tb_cameras` (`id`, `name`, `motionTimeout`, `recordOnMovement`, `prebuffering`, `videoConfig`, `mqtt`, `smtp`, `videoanalysis`, `settings`, `prebufferLength`, `create_date`, `update_dt`) VALUES
	(16, '댐영상1', 15, 0, 0, '{"source":"-i rtsp://root:bw84218899!@175.201.204.165:556/cam0_0","subSource":"-i rtsp://root:bw84218899!@175.201.204.165:556/cam0_0","stillImageSource":"-i rtsp://root:bw84218899!@175.201.204.165:556/cam0_0","stimeout":10,"audio":null,"debug":null,"rtspTransport":"tcp","vcodec":"mp4","acodec":null}', '{}', '{"email":"댐영상1"}', '{"active":false}', '{"name":"댐영상1","room":"Standard","resolution":"1280x720","pingTimeout":1,"streamTimeout":60,"audio":false,"telegramType":"Snapshot","alexa":false,"webhookUrl":"","mqttTopic":"camera.ui/motion","privacyMode":false,"camview":{"favourite":true,"live":true,"snapshotTimer":60},"dashboard":{"live":true,"snapshotTimer":60},"rekognition":{"active":false,"confidence":90,"labels":[]},"videoanalysis":{"forceCloseTimer":3,"dwellTimer":60,"sensitivity":75,"difference":5,"regions":[{"finished":true,"coords":[[0,100],[0,0],[100,0],[100,100]]}]}}', 4, '2025-06-22 14:04:05', '2025-06-22 14:04:05'),
	(17, '댐영상2', 15, 0, 0, '{"source":"-i rtsp://root:cctv1350!!@175.201.204.165:555/AVStream1_1","subSource":"-i rtsp://root:cctv1350!!@175.201.204.165:555/AVStream1_1","stillImageSource":"-i rtsp://root:cctv1350!!@175.201.204.165:555/AVStream1_1","stimeout":10,"audio":null,"debug":null,"rtspTransport":"tcp","vcodec":"mp4","acodec":null}', '{}', '{"email":"댐영상2"}', '{"active":false}', '{"name":"댐영상2","room":"Standard","resolution":"1280x720","pingTimeout":1,"streamTimeout":60,"audio":false,"telegramType":"Snapshot","alexa":false,"webhookUrl":"","mqttTopic":"camera.ui/motion","privacyMode":false,"camview":{"favourite":true,"live":true,"snapshotTimer":60},"dashboard":{"live":true,"snapshotTimer":60},"rekognition":{"active":false,"confidence":90,"labels":[]},"videoanalysis":{"forceCloseTimer":3,"dwellTimer":60,"sensitivity":75,"difference":5,"regions":[{"finished":true,"coords":[[0,100],[0,0],[100,0],[100,100]]}]}}', 4, '2025-06-22 14:04:36', '2025-06-22 14:04:36');

-- 테이블 nvrdb.tb_event_detection_zone 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_event_detection_zone` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fk_camera_id` int(11) NOT NULL DEFAULT 0,
  `zone_desc` varchar(255) NOT NULL DEFAULT '0',
  `zone_type` varchar(5) DEFAULT NULL,
  `zone_segment_json` varchar(255) NOT NULL DEFAULT '0',
  `zone_params_json` varchar(255) NOT NULL DEFAULT '0',
  `zone_active` int(11) DEFAULT 0,
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_event_detection_zone:~3 rows (대략적) 내보내기
INSERT INTO `tb_event_detection_zone` (`id`, `fk_camera_id`, `zone_desc`, `zone_type`, `zone_segment_json`, `zone_params_json`, `zone_active`, `create_date`, `update_date`) VALUES
	(20, 0, '영역1', '0', '[{"left":159,"top":155,"right":264,"bottom":245,"coords":[[159,155],[264,155],[264,245],[159,245]]}]', '{"forceCloseTimer":30,"dwellTimer":50,"sensitivity":75,"difference":50}', 1, '2025-06-22 23:06:44', '2025-06-22 23:06:44'),
	(21, 0, '영역2', '1', '[{"left":306,"top":147,"right":415,"bottom":247,"coords":[[306,147],[415,147],[415,247],[306,247]]}]', '{"forceCloseTimer":30,"dwellTimer":50,"sensitivity":75,"difference":50}', 1, '2025-06-22 23:07:15', '2025-06-22 23:07:15'),
	(23, 0, '영역3', '2', '[{"left":450,"top":141,"right":554,"bottom":242,"coords":[[450,141],[554,141],[554,242],[450,242]]}]', '{"forceCloseTimer":30,"dwellTimer":50,"sensitivity":75,"difference":50}', 1, '2025-06-22 23:07:46', '2025-06-22 23:07:46'),
	(24, 0, '영역4', '3', '[{"left":158,"top":280,"right":262,"bottom":364,"coords":[[158,280],[262,280],[262,364],[158,364]]}]', '{"forceCloseTimer":30,"dwellTimer":50,"sensitivity":75,"difference":50}', 1, '2025-06-22 23:07:56', '2025-06-22 23:07:56');

-- 테이블 nvrdb.tb_event_history 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_event_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fk_camera_id` int(11) NOT NULL DEFAULT 0,
  `camera_name` varchar(255) NOT NULL DEFAULT '0',
  `event_accur_time` datetime DEFAULT NULL,
  `event_type` varchar(5) DEFAULT NULL,
  `event_data_json` mediumtext DEFAULT NULL,
  `fk_detect_zone_id` int(11) DEFAULT 0,
  `detected_image_url` varchar(255) DEFAULT '',
  `create_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_event_history:~13 rows (대략적) 내보내기
INSERT INTO `tb_event_history` (`id`, `fk_camera_id`, `camera_name`, `event_accur_time`, `event_type`, `event_data_json`, `fk_detect_zone_id`, `detected_image_url`, `create_date`) VALUES
	(1, 4, '댐영상2', '2025-06-03 21:40:52', 'E001', '[{"label": "car", "bbox": [358, 391, 404, 439], "confidence": 0.5393124222755432}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954452.jpg', '2025-06-03 21:40:52'),
	(2, 4, '댐영상2', '2025-06-03 21:40:52', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954452.jpg', '2025-06-03 21:40:52'),
	(3, 4, '댐영상2', '2025-06-03 21:40:53', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954453.jpg', '2025-06-03 21:40:53'),
	(4, 4, '댐영상2', '2025-06-03 21:40:54', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954454.jpg', '2025-06-03 21:40:54'),
	(5, 4, '댐영상2', '2025-06-03 21:40:55', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954455.jpg', '2025-06-03 21:40:55'),
	(6, 4, '댐영상2', '2025-06-03 21:40:56', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954456.jpg', '2025-06-03 21:40:56'),
	(7, 4, '댐영상2', '2025-06-03 21:40:57', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954457.jpg', '2025-06-03 21:40:57'),
	(8, 4, '댐영상2', '2025-06-03 21:40:58', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954458.jpg', '2025-06-03 21:40:58'),
	(9, 4, '댐영상2', '2025-06-03 21:40:59', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954459.jpg', '2025-06-03 21:40:59'),
	(10, 4, '댐영상2', '2025-06-03 21:41:00', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954460.jpg', '2025-06-03 21:41:00'),
	(11, 4, '댐영상2', '2025-06-03 21:41:01', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954461.jpg', '2025-06-03 21:41:01'),
	(12, 4, '댐영상2', '2025-06-03 21:41:02', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954462.jpg', '2025-06-03 21:41:02'),
	(13, 4, '댐영상2', '2025-06-03 21:41:03', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954463.jpg', '2025-06-03 21:41:03'),
	(14, 4, '댐영상2', '2025-06-03 21:41:04', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954464.jpg', '2025-06-03 21:41:04'),
	(15, 4, '댐영상2', '2025-06-03 21:41:05', 'E001', '[{"label": "car", "bbox": [358, 393, 405, 441], "confidence": 0.3794468343257904}, {"label": "car", "bbox": [363, 227, 382, 245], "confidence": 0.3063525855541229}]', 0, '../test/camera.ui/detected_move\\2025-06-03\\댐영상2_detection_1748954465.jpg', '2025-06-03 21:41:05');

-- 테이블 nvrdb.tb_event_setting 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_event_setting` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `temperature_json` varchar(1024) DEFAULT NULL,
  `alert_json` varchar(1024) DEFAULT NULL,
  `object_json` varchar(1024) DEFAULT NULL,
  `system_json` varchar(1024) DEFAULT NULL,
  `in_page_zone` int(11) DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_event_setting:~0 rows (대략적) 내보내기
INSERT INTO `tb_event_setting` (`id`, `temperature_json`, `alert_json`, `object_json`, `system_json`, `in_page_zone`, `create_date`, `update_date`) VALUES
	(1, '{"threshold":20,"alertType":"알림","interval":30,"sensitivity":"중간","autoAlert":true}', '{"notificationType":"팝업","delay":5,"priority":"높음","repeatInterval":15,"useSound":true}', '{"detectionType":"전체","minSize":100,"accuracy":"높음","trackingDuration":10,"enableTracking":true}', '{"location_info":"수자원공사 광동댐","address":"아산시","recodingBitrate":"512k","recodingFileDeleteDays":30}', 0, '0000-00-00 00:00:00', '2025-06-30 11:17:33');

-- 테이블 nvrdb.tb_recording_history 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_recording_history` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fk_camera_id` int(11) NOT NULL DEFAULT 0,
  `fk_schedule_id` int(11) NOT NULL DEFAULT 0,
  `camera_name` varchar(100) NOT NULL DEFAULT '0',
  `start_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `duration` int(11) DEFAULT 0,
  `file_path` varchar(1024) DEFAULT NULL,
  `file_size` int(11) DEFAULT 0,
  `record_type` varchar(20) DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `resolution` varchar(20) DEFAULT NULL,
  `bitrate` int(11) DEFAULT 0,
  `framerate` int(11) DEFAULT 0,
  `codec` varchar(20) DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_recording_history:~7 rows (대략적) 내보내기
INSERT INTO `tb_recording_history` (`id`, `fk_camera_id`, `fk_schedule_id`, `camera_name`, `start_time`, `end_time`, `duration`, `file_path`, `file_size`, `record_type`, `status`, `resolution`, `bitrate`, `framerate`, `codec`, `create_date`, `update_date`) VALUES
	(1, 17, 12, '댐영상2', '2025-06-30 13:35:45', '2025-06-30 13:35:51', 0, '댐영상2_2025-06-30T13-35-45.mp4', 0, NULL, 'error', NULL, 0, 0, NULL, NULL, NULL),
	(2, 17, 12, '댐영상2', '2025-06-30 13:36:15', '2025-06-30 13:36:21', 0, '댐영상2_2025-06-30T13-36-15.mp4', 0, NULL, 'error', NULL, 0, 0, NULL, NULL, NULL),
	(3, 17, 12, '댐영상2', '2025-06-30 13:36:45', '2025-06-30 13:36:50', 0, '댐영상2_2025-06-30T13-36-45.mp4', 0, NULL, 'error', NULL, 0, 0, NULL, NULL, NULL),
	(4, 17, 13, '댐영상2', '2025-06-30 13:41:02', '2025-06-30 13:41:07', 0, '댐영상2_2025-06-30T13-41-02.mp4', 0, NULL, 'error', NULL, 0, 0, NULL, NULL, NULL),
	(5, 17, 13, '댐영상2', '2025-06-30 13:41:32', '2025-06-30 13:41:37', 0, '댐영상2_2025-06-30T13-41-32.mp4', 0, NULL, 'error', NULL, 0, 0, NULL, NULL, NULL),
	(6, 17, 14, '댐영상2', '2025-06-30 13:45:36', '2025-06-30 13:47:06', 0, '댐영상2_2025-06-30T13-45-36.mp4', 0, NULL, 'completed', NULL, 0, 0, NULL, NULL, NULL),
	(7, 17, 15, '댐영상2', '2025-06-30 13:49:06', '2025-06-30 13:50:06', 0, '댐영상2_2025-06-30T13-49-06.mp4', 0, NULL, 'completed', NULL, 0, 0, NULL, NULL, NULL);

-- 테이블 nvrdb.tb_schedules 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_schedules` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fk_camera_id` int(11) NOT NULL DEFAULT 0,
  `cameraName` varchar(255) NOT NULL DEFAULT '0',
  `days_of_week` varchar(255) DEFAULT NULL,
  `start_time` varchar(5) DEFAULT NULL,
  `end_time` varchar(5) DEFAULT NULL,
  `recording_type` varchar(50) DEFAULT NULL,
  `isActive` int(11) DEFAULT 0,
  `source` varchar(255) DEFAULT '',
  `create_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `recoding_bitrate` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4;

-- 테이블 데이터 nvrdb.tb_schedules:~0 rows (대략적) 내보내기
INSERT INTO `tb_schedules` (`id`, `fk_camera_id`, `cameraName`, `days_of_week`, `start_time`, `end_time`, `recording_type`, `isActive`, `source`, `create_date`, `update_date`, `recoding_bitrate`) VALUES
	(15, 17, '댐영상2', '[1]', '13:48', '13:50', 'Video', 1, '-i rtsp://root:cctv1350!!@175.201.204.165:555/AVStream1_1', '2025-06-30 13:48:39', '2025-06-30 13:48:39', '1024k');

-- 테이블 nvrdb.tb_users 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `userId` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `userName` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `userDept` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `password` varchar(255) CHARACTER SET utf8mb4 NOT NULL,
  `permissionLevel` int(11) NOT NULL DEFAULT 1,
  `sessionTimer` int(11) DEFAULT NULL,
  `createdAt` datetime NOT NULL,
  `updatedAt` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`userId`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

-- 테이블 데이터 nvrdb.tb_users:~1 rows (대략적) 내보내기
INSERT INTO `tb_users` (`id`, `userId`, `userName`, `userDept`, `password`, `permissionLevel`, `sessionTimer`, `createdAt`, `updatedAt`) VALUES
	(1, 'akj', '안근진', '연구소', 'HU4udeJjfJK4cZaUzjmZzA==$MJ9VdGYNw7878oL0TWEsMBya07pSup/yhbSItb2gkbHdQQQyX+Mg18hyJRsZiGJYYAX6GsrpyVmf1LzLmrEB4Q==', 2, 14400, '2025-05-07 05:09:05', '2025-05-07 05:09:05'),
	(10, 'akj2995', '안근진2', '경영기획실', 'NT1ULA9wT0Ml5jAABu3L4A==$RDP+bDEfNmyhor8+ZUKsty+/4ET6CjNULaOoAme2edkrEuDGFZMjjOU8ibDj//JAQDGKZ3IGiSjXKiFuF7T3iA==', 1, 14400, '2025-05-28 09:53:10', '2025-05-28 09:53:47');

-- 테이블 nvrdb.tb_video_receive_data 구조 내보내기
CREATE TABLE IF NOT EXISTS `tb_video_receive_data` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fk_camera_id` int(11) NOT NULL,
  `create_date` datetime NOT NULL DEFAULT current_timestamp(),
  `data_raw` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`data_raw`)),
  `data_value` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`data_value`)),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

-- 테이블 데이터 nvrdb.tb_video_receive_data:~0 rows (대략적) 내보내기

-- 테이블 nvrdb.tokens 구조 내보내기
CREATE TABLE IF NOT EXISTS `tokens` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `token` varchar(300) COLLATE latin1_general_ci NOT NULL,
  `valid` tinyint(1) NOT NULL DEFAULT 1,
  `createdAt` datetime NOT NULL,
  `updatedAt` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=latin1 COLLATE=latin1_general_ci;

-- 테이블 데이터 nvrdb.tokens:~0 rows (대략적) 내보내기

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
