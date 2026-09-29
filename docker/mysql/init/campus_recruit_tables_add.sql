-- =====================================================
-- campus-recruit-ai-platform 增量建表脚本
-- 适用：campus_recruit 库已存在（含 sys_user），仅需新增 9 张业务表
-- 执行：mysql -h127.0.0.1 -uroot -p123456 campus_recruit < campus_recruit_tables_add.sql
-- 全局规范：BIGINT 雪花主键 / utf8mb4_unicode_ci / InnoDB / 审计字段 / 逻辑删除
-- =====================================================

USE campus_recruit;

-- =====================================================
-- 1. user_profile 用户求职画像表
-- 每个用户一条画像，供岗位匹配 Agent 和长期记忆使用
-- =====================================================
DROP TABLE IF EXISTS user_profile;
CREATE TABLE user_profile (
  id               BIGINT       NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  user_id          BIGINT       NOT NULL COMMENT '用户ID（关联 sys_user.id）',
  target_position  VARCHAR(64)  DEFAULT '' COMMENT '目标岗位，如 后端开发工程师',
  target_industry  VARCHAR(32)  DEFAULT '' COMMENT '目标行业，如 互联网/金融/制造',
  city_preference  VARCHAR(64)  DEFAULT '' COMMENT '意向城市，多个用逗号分隔，如 北京,上海',
  education        TINYINT      NOT NULL DEFAULT 0 COMMENT '学历：0其他 1本科 2硕士 3博士',
  school           VARCHAR(64)  DEFAULT '' COMMENT '学校名称',
  major            VARCHAR(64)  DEFAULT '' COMMENT '专业名称',
  graduation_year  INT          DEFAULT NULL COMMENT '毕业年份，如 2027',
  skill_tags       VARCHAR(1000) DEFAULT '[]' COMMENT '技能标签JSON数组字符串，如["Java","Spring"]',
  career_intention VARCHAR(1000) DEFAULT '' COMMENT '求职意向描述，如 期望从事后端开发，倾向大厂',
  self_evaluation  VARCHAR(2000) DEFAULT '' COMMENT '自我评价，由Agent生成或用户填写',
  status           TINYINT      NOT NULL DEFAULT 1 COMMENT '状态：1启用 0停用',
  create_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted       TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户求职画像表';

-- =====================================================
-- 2. job_position 校招岗位表
-- 核心表，由采集 Agent 每日增量写入，支撑岗位匹配
-- =====================================================
DROP TABLE IF EXISTS job_position;
CREATE TABLE job_position (
  id                   BIGINT       NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  company_name         VARCHAR(64)  NOT NULL COMMENT '公司名称',
  position_name        VARCHAR(64)  NOT NULL COMMENT '岗位名称',
  industry             VARCHAR(32)  DEFAULT '' COMMENT '行业，如 互联网/金融',
  job_category         VARCHAR(32)  DEFAULT '' COMMENT '岗位类别，如 后端开发/前端开发/AI算法/测试/产品/运营',
  work_city            VARCHAR(64)  DEFAULT '' COMMENT '工作地点，如 北京/上海/远程',
  salary_min           DECIMAL(10,2) DEFAULT NULL COMMENT '月薪下限，单位K，如 15 表示15K',
  salary_max           DECIMAL(10,2) DEFAULT NULL COMMENT '月薪上限，单位K，如 25 表示25K',
  salary_note          VARCHAR(64)  DEFAULT '' COMMENT '薪资原文，如 15-25K·14薪',
  education_requirement TINYINT     NOT NULL DEFAULT 0 COMMENT '学历要求：0不限 1本科 2硕士 3博士',
  education_text       VARCHAR(32)  DEFAULT '' COMMENT '学历要求原文，如 本科及以上',
  job_description      MEDIUMTEXT   COMMENT '岗位职责描述',
  job_requirement      MEDIUMTEXT   COMMENT '任职要求',
  source_channel       VARCHAR(32)  DEFAULT '' COMMENT '来源渠道，如 牛客/官网/智联',
  source_url           VARCHAR(512) DEFAULT '' COMMENT '原文链接',
  job_hash             CHAR(32)     NOT NULL COMMENT '去重指纹MD5(公司+岗位+城市+链接)',
  publish_time         DATE         DEFAULT NULL COMMENT '发布时间',
  deadline             DATETIME     DEFAULT NULL COMMENT '投递截止时间',
  status               TINYINT      NOT NULL DEFAULT 1 COMMENT '状态：1在招 0已下架',
  create_time          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted           TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  UNIQUE KEY uk_job_hash (job_hash),
  KEY idx_status_deadline (status, deadline),
  KEY idx_category (job_category),
  KEY idx_city (work_city),
  KEY idx_company (company_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='校招岗位表';

-- =====================================================
-- 3. resume_record 简历优化记录表
-- 每次简历优化生成一条记录，供历史查询和能力复盘
-- =====================================================
DROP TABLE IF EXISTS resume_record;
CREATE TABLE resume_record (
  id                      BIGINT      NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  user_id                 BIGINT      NOT NULL COMMENT '用户ID（关联 sys_user.id）',
  resume_title            VARCHAR(64) DEFAULT '' COMMENT '简历标题',
  original_content        MEDIUMTEXT  COMMENT '原始简历文本',
  optimized_content       MEDIUMTEXT  COMMENT '优化后简历文本',
  target_position_name    VARCHAR(64) DEFAULT '' COMMENT '目标岗位名称',
  optimization_suggestions MEDIUMTEXT COMMENT '优化建议JSON字符串',
  resume_score            INT         DEFAULT NULL COMMENT '优化前评分0-100',
  optimized_score         INT         DEFAULT NULL COMMENT '优化后评分0-100',
  status                  TINYINT     NOT NULL DEFAULT 0 COMMENT '状态：1已完成 0处理中',
  create_time             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted              TINYINT     NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='简历优化记录表';

-- =====================================================
-- 4. interview_record 模拟面试记录表
-- 一次完整面试一条记录
-- =====================================================
DROP TABLE IF EXISTS interview_record;
CREATE TABLE interview_record (
  id                BIGINT      NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  user_id           BIGINT      NOT NULL COMMENT '用户ID（关联 sys_user.id）',
  interview_type    TINYINT     NOT NULL DEFAULT 1 COMMENT '面试类型：1技术面 2HR面',
  target_company    VARCHAR(64) DEFAULT '' COMMENT '目标公司',
  target_position   VARCHAR(64) DEFAULT '' COMMENT '目标岗位',
  difficulty_level  TINYINT     NOT NULL DEFAULT 1 COMMENT '难度：1简单 2中等 3困难',
  duration_seconds  INT         NOT NULL DEFAULT 0 COMMENT '面试时长，单位秒',
  question_count    INT         NOT NULL DEFAULT 0 COMMENT '提问数量',
  overall_score     INT         DEFAULT NULL COMMENT '综合评分0-100',
  evaluation_report MEDIUMTEXT  COMMENT '面试复盘报告',
  status            TINYINT     NOT NULL DEFAULT 1 COMMENT '状态：1进行中 2已完成 3已中断',
  create_time       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time       DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted        TINYINT     NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_user_type (user_id, interview_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='模拟面试记录表';

-- =====================================================
-- 5. interview_message 面试消息表
-- 面试过程的逐条对话记录，支撑复盘报告生成和长期记忆沉淀
-- =====================================================
DROP TABLE IF EXISTS interview_message;
CREATE TABLE interview_message (
  id                  BIGINT      NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  interview_record_id BIGINT      NOT NULL COMMENT '模拟面试记录ID（关联 interview_record.id）',
  role                VARCHAR(16) NOT NULL COMMENT '消息角色：user 用户 assistant AI面试官',
  message_type        VARCHAR(16) NOT NULL DEFAULT 'question' COMMENT '消息类型：question问题 answer回答 evaluation点评',
  content             MEDIUMTEXT  COMMENT '消息内容',
  score               INT         DEFAULT NULL COMMENT '本条点评评分0-100，非点评消息为空',
  create_time         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time         DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted          TINYINT     NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_record_id (interview_record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试消息表';

-- =====================================================
-- 6. session_record 用户会话记录表
-- 记录用户每次任务会话，供历史记录页和个人中心展示
-- =====================================================
DROP TABLE IF EXISTS session_record;
CREATE TABLE session_record (
  id           BIGINT       NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  user_id      BIGINT       NOT NULL COMMENT '用户ID（关联 sys_user.id）',
  session_type TINYINT      NOT NULL DEFAULT 1 COMMENT '会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答',
  agent_name   VARCHAR(32)  DEFAULT '' COMMENT '处理的Agent名称，如 MatchAgent/ResumeAgent',
  title        VARCHAR(128) DEFAULT '' COMMENT '会话标题',
  summary      VARCHAR(2000) DEFAULT '' COMMENT '会话摘要',
  status       TINYINT      NOT NULL DEFAULT 1 COMMENT '状态：1进行中 2已完成',
  create_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted   TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_user_type (user_id, session_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户会话记录表';

-- =====================================================
-- 7. ability_profile 能力画像快照表
-- 每次面试复盘生成一组各维度快照，可绘制能力成长曲线，是长期记忆的核心载体
-- =====================================================
DROP TABLE IF EXISTS ability_profile;
CREATE TABLE ability_profile (
  id              BIGINT       NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  user_id         BIGINT       NOT NULL COMMENT '用户ID（关联 sys_user.id）',
  dimension       VARCHAR(32)  NOT NULL COMMENT '能力维度，如 技术基础/项目经验/沟通表达/逻辑思维/岗位匹配度',
  dimension_score INT          NOT NULL DEFAULT 0 COMMENT '得分0-100',
  evaluation      VARCHAR(1000) DEFAULT '' COMMENT '维度评语',
  snapshot_date   DATE         NOT NULL COMMENT '快照日期',
  create_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted      TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_user_dimension (user_id, dimension),
  KEY idx_snapshot (snapshot_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='能力画像快照表';

-- =====================================================
-- 8. knowledge_doc 知识库文档表
-- RAG 静态知识库的文档管理，由后台任务分块向量化写入 Milvus
-- =====================================================
DROP TABLE IF EXISTS knowledge_doc;
CREATE TABLE knowledge_doc (
  id            BIGINT       NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  doc_title     VARCHAR(128) NOT NULL COMMENT '文档标题',
  doc_type      TINYINT      NOT NULL DEFAULT 1 COMMENT '文档类型：1面经 2简历模板 3面试技巧 4行业知识 5岗位知识',
  content       MEDIUMTEXT   COMMENT '文档原文',
  chunk_count   INT          NOT NULL DEFAULT 0 COMMENT '分块数量，默认0表示未分块',
  vector_status TINYINT      NOT NULL DEFAULT 0 COMMENT '向量化状态：0未向量化 1已向量化',
  source        VARCHAR(255) DEFAULT '' COMMENT '来源，如 用户上传/后台采集/人工录入',
  create_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted    TINYINT      NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_type_status (doc_type, vector_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='知识库文档表';

-- =====================================================
-- 9. collector_log 采集任务日志表
-- 记录每日采集任务执行情况，支撑论文数据治理章节和采集监控
-- =====================================================
DROP TABLE IF EXISTS collector_log;
CREATE TABLE collector_log (
  id              BIGINT        NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  collector_name  VARCHAR(64)   NOT NULL COMMENT '采集器名称，如 牛客校招采集器',
  source_channel  VARCHAR(32)   DEFAULT '' COMMENT '来源渠道，如 牛客/官网/智联',
  total_count     INT           NOT NULL DEFAULT 0 COMMENT '本次采集总数',
  new_count       INT           NOT NULL DEFAULT 0 COMMENT '新增数',
  update_count    INT           NOT NULL DEFAULT 0 COMMENT '更新数',
  fail_count      INT           NOT NULL DEFAULT 0 COMMENT '失败数',
  status          TINYINT       NOT NULL DEFAULT 3 COMMENT '状态：1成功 2部分成功 3失败',
  error_msg       VARCHAR(2000) DEFAULT NULL COMMENT '错误信息，失败时记录',
  start_time      DATETIME      DEFAULT NULL COMMENT '开始时间',
  end_time        DATETIME      DEFAULT NULL COMMENT '结束时间',
  cost_ms         INT           NOT NULL DEFAULT 0 COMMENT '耗时，单位毫秒',
  create_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted      TINYINT       NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_start_time (start_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='采集任务日志表';

-- =====================================================
-- 10. 长期用户记忆表 user_memory
-- 论文"长期记忆"模块载体：MySQL 存原文/元数据 + Milvus 存语义向量，双写一致
-- =====================================================
DROP TABLE IF EXISTS user_memory;
CREATE TABLE user_memory (
  id            BIGINT         NOT NULL COMMENT '主键（雪花算法，应用层生成）',
  user_id       BIGINT         NOT NULL COMMENT '用户ID（关联 sys_user.id）',
  memory_type   TINYINT        NOT NULL DEFAULT 5 COMMENT '记忆类型：1能力画像 2项目经历 3技能偏好 4面试教训 5其他',
  content       VARCHAR(2000)  NOT NULL COMMENT '长期记忆条目内容',
  importance    TINYINT        NOT NULL DEFAULT 2 COMMENT '重要度：1低 2中 3高',
  source        VARCHAR(64)    DEFAULT '自由问答' COMMENT '来源：面试复盘/简历优化/自由问答',
  content_hash  CHAR(32)       NOT NULL DEFAULT '' COMMENT '内容 MD5(小写)，用于跨进程幂等与去重',
  vector_status TINYINT        NOT NULL DEFAULT 0 COMMENT '向量化状态：0未向量化 1已向量化',
  create_time   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  update_time   DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  is_deleted    TINYINT        NOT NULL DEFAULT 0 COMMENT '逻辑删除：0未删除 1已删除',
  PRIMARY KEY (id),
  KEY idx_user_create (user_id, create_time),
  KEY idx_source (source),
  UNIQUE KEY uk_user_hash (user_id, content_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='长期用户记忆表';

-- 完成：10 张新表创建完毕
