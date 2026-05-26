-- 数据库迁移脚本
-- 用于更新现有数据库结构

USE baby;

-- 1. 检查并添加username字段到users表（如果不存在）
-- 注意：MySQL 8.0不支持ADD COLUMN IF NOT EXISTS，需要先检查
SET @has_username = (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'baby' AND table_name = 'users' AND column_name = 'username');
SET @sql = IF(@has_username = 0, 'ALTER TABLE users ADD COLUMN username VARCHAR(100) NOT NULL DEFAULT ''', 'SELECT "username字段已存在"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 2. 检查并添加last_active字段到device表（如果不存在）
SET @has_last_active = (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = 'baby' AND table_name = 'device' AND column_name = 'last_active');
SET @sql = IF(@has_last_active = 0, 'ALTER TABLE device ADD COLUMN last_active DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP', 'SELECT "last_active字段已存在"');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 3. 更新现有用户的username（如果为空）
UPDATE users SET username = SUBSTRING_INDEX(email, '@', 1) WHERE username = '' OR username IS NULL;

-- 4. 创建索引以提高查询性能
-- 注意：如果索引已存在会报错，可以忽略
CREATE INDEX idx_device_email ON device(email);
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_device_id ON notifications(device_id);
CREATE INDEX idx_notifications_timestamp ON notifications(timestamp);

-- 5. 验证表结构
SELECT 'users表结构:' as info;
DESCRIBE users;

SELECT 'device表结构:' as info;
DESCRIBE device;

SELECT 'notifications表结构:' as info;
DESCRIBE notifications;

-- 6. 统计数据
SELECT '数据统计:' as info;
SELECT COUNT(*) as user_count FROM users;
SELECT COUNT(*) as device_count FROM device;
SELECT COUNT(*) as notification_count FROM notifications;
