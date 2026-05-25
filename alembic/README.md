# Alembic 数据库迁移

## 初始化

1. 初始化Alembic：
```bash
alembic init alembic
```

2. 配置数据库连接：
编辑 `alembic.ini` 文件中的 `sqlalchemy.url`，或使用环境变量。

3. 创建初始迁移：
```bash
alembic revision --autogenerate -m "Initial migration"
```

4. 应用迁移：
```bash
alembic upgrade head
```

## 常用命令

### 创建新迁移
```bash
alembic revision --autogenerate -m "描述信息"
```

### 应用迁移
```bash
# 应用所有迁移
alembic upgrade head

# 应用下一个迁移
alembic upgrade +1

# 应用到特定版本
alembic upgrade <revision_id>
```

### 回滚迁移
```bash
# 回滚上一个迁移
alembic downgrade -1

# 回滚到特定版本
alembic downgrade <revision_id>

# 回滚所有迁移
alembic downgrade base
```

### 查看迁移历史
```bash
# 查看当前版本
alembic current

# 查看历史
alembic history

# 查看最新迁移
alembic heads
```

### 生成SQL脚本
```bash
# 生成从当前到最新的SQL
alembic upgrade head --sql > migration.sql

# 生成从特定版本到最新的SQL
alembic upgrade <revision_id>:head --sql > migration.sql
```

## 配置

### 环境变量
在 `.env` 文件中配置：
```
DATABASE_URL=mysql+pymysql://user:password@localhost/database
```

### 迁移脚本位置
默认位置：`alembic/versions/`

## 最佳实践

1. **命名规范**：使用描述性的迁移名称
   ```bash
   alembic revision --autogenerate -m "Add user table"
   alembic revision --autogenerate -m "Add email index to users"
   ```

2. **检查生成的迁移**：自动生成的迁移可能需要手动调整

3. **测试迁移**：在测试环境中先测试迁移

4. **备份数据库**：在生产环境执行迁移前备份数据库

5. **版本控制**：将迁移脚本提交到版本控制系统

## 故障排除

### 迁移冲突
如果多个开发者同时创建迁移，可能会导致冲突：
```bash
# 合并迁移
alembic merge heads -m "Merge migrations"
```

### 重置迁移
```bash
# 删除所有迁移文件
rm alembic/versions/*.py

# 重新创建初始迁移
alembic revision --autogenerate -m "Initial migration"
```

### 手动标记版本
如果数据库已经存在但没有迁移历史：
```bash
# 标记当前版本
alembic stamp head
```
