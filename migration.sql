-- 数据库迁移脚本
-- 用于更新现有数据库结构

USE baby;

-- 1. 检查并添加username字段到users表（如果不存在）
-- 注意：如果username字段已存在，此语句会报错，可以忽略
ALTER TABLE users ADD COLUMN username VARCHAR(100) NOT NULL DEFAULT '';

-- 2. 检查并添加last_active字段到device表（如果不存在）
-- 注意：如果last_active字段已存在，此语句会报错，可以忽略
ALTER TABLE device ADD COLUMN last_active DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- 3. 更新现有用户的username（如果为空）
UPDATE users SET username = SUBSTRING_INDEX(email, '@', 1) WHERE username = '' OR username IS NULL;

-- 4. 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_device_email ON device(email);
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_device_id ON notifications(device_id);
CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp);

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
