-- Baby Monitor 数据库初始化脚本

USE baby;

-- 创建users表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    username VARCHAR(100) NOT NULL
);

-- 创建device表
CREATE TABLE IF NOT EXISTS device (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    rtsp_url TEXT NOT NULL,
    ip VARCHAR(45) NOT NULL,
    status ENUM('online', 'offline') NOT NULL DEFAULT 'offline',
    email VARCHAR(255) NOT NULL,
    last_active DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 创建notifications表
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    device_id INT,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (device_id) REFERENCES device(id) ON DELETE SET NULL
);

-- 插入测试数据
INSERT INTO users (email, hashed_password, username) VALUES
('test@example.com', '$2b$12$LJ3m4ys3Lz0YBNOBRQz6O.7LHd7Y1g3b3b3b3b3b3b3b3b3b3b3b', 'testuser');

INSERT INTO device (name, email, ip, status, rtsp_url) VALUES
('设备1', 'test@example.com', '192.168.1.100', 'online', 'rtsp://admin:password@192.168.1.100:554/stream1'),
('设备2', 'test@example.com', '192.168.1.101', 'offline', 'rtsp://admin:password@192.168.1.101:554/stream1');

INSERT INTO notifications (user_id, device_id, level, message, timestamp, pinned, deleted) VALUES
(1, 1, 'safe', '婴儿正在正常活动', NOW(), false, false),
(1, 1, 'warning', '婴儿趴着睡觉时间过长', NOW(), false, false),
(1, 2, 'danger', '婴儿可能跌倒了', NOW(), false, false);
