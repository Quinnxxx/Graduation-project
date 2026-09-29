-- =====================================================
-- campus-recruit-ai-platform 数据库验证脚本
-- 执行：mysql -h127.0.0.1 -uroot -p123456 campus_recruit < verify_tables.sql
-- 验证目标：表数量 / 关键表结构 / 唯一索引与主要索引
-- =====================================================

USE campus_recruit;

-- 1. 确认 10 张表存在
SELECT '===== 1. 表清单（应为 10 张）=====' AS step;
SHOW TABLES;

-- 2. 逐表统计字段数（10 张表均应有审计三字段：create_time/update_time/is_deleted）
SELECT '===== 2. 每张表字段总数 =====' AS step;
SELECT
  table_name   AS '表名',
  table_rows   AS '估算行数',
  table_comment AS '表备注'
FROM information_schema.tables
WHERE table_schema = 'campus_recruit'
ORDER BY table_name;

-- 3. 抽查：user_profile（唯一索引 uk_user_id）
SELECT '===== 3. DESC user_profile =====' AS step;
DESC user_profile;

-- 4. 抽查：job_position 唯一索引与主要索引
SELECT '===== 4. job_position 索引确认 =====' AS step;
SHOW INDEX FROM job_position;

-- 5. 抽查：interview_record 联合索引 idx_user_type
SELECT '===== 5. interview_record 索引确认 =====' AS step;
SHOW INDEX FROM interview_record;

-- 6. 抽查：sys_user（原有表）字段完整性
SELECT '===== 6. DESC sys_user =====' AS step;
DESC sys_user;

-- 7. 统一校验：所有表均含审计字段（create_time/update_time/is_deleted）
SELECT '===== 7. 审计字段完整性检查（缺失应返回 0 行）=====' AS step;
SELECT
  table_name AS '表名',
  GROUP_CONCAT(column_name ORDER BY ordinal_position) AS '缺失字段'
FROM information_schema.columns
WHERE table_schema = 'campus_recruit'
  AND table_name IN ('sys_user','user_profile','job_position','resume_record',
                     'interview_record','interview_message','session_record',
                     'ability_profile','knowledge_doc','collector_log')
  AND column_name IN ('create_time','update_time','is_deleted')
GROUP BY table_name
HAVING COUNT(DISTINCT column_name) < 3;

-- 8. 唯一索引核对：uk_username / uk_user_id / uk_job_hash 应全部存在
SELECT '===== 8. 唯一索引核对（应返回 3 行）=====' AS step;
SELECT table_name AS '表名', index_name AS '唯一索引'
FROM information_schema.statistics
WHERE table_schema = 'campus_recruit'
  AND index_name IN ('uk_username','uk_user_id','uk_job_hash')
  AND non_unique = 0
ORDER BY table_name;
