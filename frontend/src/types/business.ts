/**
 * 业务领域类型定义
 *
 * 与 business-service 的 VO / DTO 字段一一对齐（统一 camelCase），
 * 字段命名以后端 Java 类为准，禁止前端自行猜测。
 *
 * 约定：
 * - 主键 / 计数 / 金额等数值统一为 number（后端 Long / BigDecimal 经 JSON 序列化）；
 * - 日期时间（LocalDate / LocalDateTime）统一以 string 承载（ISO 字符串）；
 * - 后端可能为空的字段以可选（?）标注。
 */

/* ============================ 校招岗位 ============================ */

/**
 * 校招岗位信息（对应后端 JobPositionVO）
 */
export interface JobPosition {
  /**
   * 岗位 ID（雪花算法 18 位 BIGINT）
   *
   * 经 request.ts 的 json-bigint 解析为字符串，避免超出 JS 安全整数范围丢精度。
   */
  id: string
  /** 公司名称 */
  companyName: string
  /** 岗位名称 */
  positionName: string
  /** 行业 */
  industry?: string
  /** 岗位类别，如 后端开发/前端开发/AI算法/测试/产品/运营 */
  jobCategory?: string
  /** 工作城市 */
  workCity?: string
  /** 月薪下限（单位 K） */
  salaryMin?: number
  /** 月薪上限（单位 K） */
  salaryMax?: number
  /** 薪资原文，如 25-45K·16薪 */
  salaryNote?: string
  /** 学历要求：0不限 1本科 2硕士 3博士 */
  educationRequirement?: number
  /** 学历要求原文，如 本科及以上 */
  educationText?: string
  /** 岗位职责描述 */
  jobDescription?: string
  /** 任职要求 */
  jobRequirement?: string
  /** 来源渠道 */
  sourceChannel?: string
  /** 原文链接 */
  sourceUrl?: string
  /** 发布时间（日期字符串） */
  publishTime?: string
  /** 投递截止时间（时间字符串） */
  deadline?: string
  /** 状态：1在招 0已下架 */
  status?: number
  /** 创建时间 */
  createTime?: string
}

/**
 * 校招岗位分页查询参数（对应后端 JobPositionQueryDTO）
 *
 * 仅分页字段必填（后端有默认值 1/10），其余筛选条件可选；
 * status 不传时查询全部状态。
 */
export interface JobPositionQuery {
  /** 当前页码，默认 1 */
  pageNum: number
  /** 每页条数，默认 10，最大 100 */
  pageSize: number
  /** 关键词，模糊匹配岗位名称/公司名称/JD 文本 */
  keyword?: string
  /** 公司名称（模糊匹配） */
  companyName?: string
  /** 岗位类别（精确匹配），如 后端开发/前端开发/AI算法/测试/产品/运营 */
  jobCategory?: string
  /** 工作城市（精确匹配） */
  workCity?: string
  /** 行业（精确匹配） */
  industry?: string
  /** 学历要求：0不限 1本科 2硕士 3博士 */
  educationRequirement?: number
  /** 薪资下限(K)，筛选岗位薪资上限 >= 该值 */
  salaryMin?: number
  /** 薪资上限(K)，筛选岗位薪资下限 <= 该值 */
  salaryMax?: number
  /** 状态：1在招 0已下架，不传查全部 */
  status?: number
}

/** 名称-数量统计项（对应后端 JobStatsVO.NameCountVO） */
export interface NameCount {
  /** 分组名称（岗位类别或城市） */
  name: string
  /** 数量 */
  count: number
}

/** 校招岗位统计（对应后端 JobStatsVO，仅统计在招岗位） */
export interface JobStats {
  /** 在招岗位总数 */
  totalCount: number
  /** 按岗位类别分组计数 */
  categoryCounts: NameCount[]
  /** 按城市分组计数（Top10） */
  cityCounts: NameCount[]
}

/* ============================ 用户求职画像 ============================ */

/** 学历枚举：0其他 1本科 2硕士 3博士 */
export type EducationLevel = 0 | 1 | 2 | 3

/**
 * 用户求职画像（对应后端 UserProfileVO）
 *
 * 每个用户一条画像；skillTags 以字符串数组返回（后端存储为 JSON 字符串，
 * 由业务服务完成转换）。
 */
export interface UserProfile {
  /** 用户 ID（画像唯一归属，对应唯一索引 uk_user_id） */
  userId: number
  /** 目标岗位 */
  targetPosition?: string
  /** 目标行业 */
  targetIndustry?: string
  /** 意向城市 */
  cityPreference?: string
  /** 学历：0其他 1本科 2硕士 3博士 */
  education?: EducationLevel | number
  /** 学校 */
  school?: string
  /** 专业 */
  major?: string
  /** 毕业年份 */
  graduationYear?: number
  /** 技能标签列表，如 ["Java","Spring"] */
  skillTags?: string[]
  /** 求职意向描述 */
  careerIntention?: string
  /** 自我评价 */
  selfEvaluation?: string
  /** 状态：1启用 0停用 */
  status?: number
}

/**
 * 创建/更新用户画像参数（对应后端 UserProfileSaveDTO）
 *
 * 字段级更新约定：null/不传表示不修改；skillTags 传空数组 [] 表示清空技能标签。
 */
export interface UserProfileSaveParams {
  /** 目标岗位 */
  targetPosition?: string
  /** 目标行业 */
  targetIndustry?: string
  /** 意向城市 */
  cityPreference?: string
  /** 学历：0其他 1本科 2硕士 3博士 */
  education?: EducationLevel | number
  /** 学校 */
  school?: string
  /** 专业 */
  major?: string
  /** 毕业年份（2000-2100） */
  graduationYear?: number
  /** 技能标签列表（允许空数组） */
  skillTags?: string[]
  /** 求职意向描述 */
  careerIntention?: string
  /** 自我评价 */
  selfEvaluation?: string
}

/* ============================ 简历记录 ============================ */

/** 简历处理状态：0处理中 1已完成 */
export type ResumeStatus = 0 | 1

/**
 * 简历优化记录（对应后端 ResumeVO）
 */
export interface ResumeRecord {
  /** 记录 ID */
  id: number
  /** 用户 ID */
  userId: number
  /** 简历标题 */
  resumeTitle: string
  /** 原始简历文本 */
  originalContent: string
  /** 优化后简历文本 */
  optimizedContent?: string
  /** 目标岗位名称 */
  targetPositionName?: string
  /** 优化建议（JSON 字符串） */
  optimizationSuggestions?: string
  /** 优化前评分 0-100 */
  resumeScore?: number
  /** 优化后评分 0-100 */
  optimizedScore?: number
  /** 状态：1已完成 0处理中 */
  status: ResumeStatus | number
  /** 上传简历原始文件名（PDF 上传后随创建请求回传） */
  fileName?: string
  /** 简历文件字节数 */
  fileSize?: number
  /** 创建时间 */
  createTime?: string
  /** 更新时间 */
  updateTime?: string
}

/** 创建简历记录参数（对应后端 ResumeSaveDTO） */
export interface ResumeSaveParams {
  /** 简历标题 */
  resumeTitle: string
  /** 原始简历文本 */
  originalContent: string
  /** 目标岗位名称（可选） */
  targetPositionName?: string
  /** 上传简历原始文件名（PDF 上传后回填） */
  fileName?: string
  /** 简历文件存储相对路径（PDF 上传后回填） */
  filePath?: string
  /** 简历文件字节数 */
  fileSize?: number
}

/**
 * 简历 PDF 上传结果（对应后端 ResumeUploadVO，POST /resumes/upload）
 */
export interface ResumeUploadResult {
  /** 上传简历原始文件名 */
  fileName: string
  /** 简历文件字节数 */
  fileSize: number
  /** 简历文件存储相对路径（随创建请求回传，落库用） */
  filePath: string
  /** PDF 提取出的简历文本 */
  text: string
}

/**
 * 更新简历记录参数（对应后端 ResumeUpdateDTO，AI 优化回填）
 *
 * 字段级更新约定：null/不传表示不修改。
 */
export interface ResumeUpdateParams {
  /** 优化后简历文本 */
  optimizedContent?: string
  /** 优化建议（JSON 字符串） */
  optimizationSuggestions?: string
  /** 优化前评分 0-100 */
  resumeScore?: number
  /** 优化后评分 0-100 */
  optimizedScore?: number
  /** 状态：1已完成 0处理中 */
  status?: ResumeStatus | number
}

/** 简历记录分页查询参数（对应后端 ResumeQueryDTO） */
export interface ResumePageParams {
  /** 当前页码，默认 1 */
  pageNum?: number
  /** 每页条数，默认 10，最大 100 */
  pageSize?: number
}

/* ============================ 用户会话 ============================ */

/** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
export type SessionType = 1 | 2 | 3 | 4 | 5

/** 会话状态：1进行中 2已完成 */
export type SessionStatus = 1 | 2

/**
 * 用户会话记录（对应后端 SessionVO）
 */
export interface SessionRecord {
  /** 会话 ID */
  id: number
  /** 用户 ID */
  userId: number
  /** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
  sessionType: SessionType | number
  /** 处理的 Agent 名称 */
  agentName?: string
  /** 会话标题 */
  title?: string
  /** 会话摘要 */
  summary?: string
  /** 状态：1进行中 2已完成 */
  status: SessionStatus | number
  /** 创建时间 */
  createTime?: string
  /** 更新时间 */
  updateTime?: string
}

/** 创建用户会话参数（对应后端 SessionCreateDTO） */
export interface SessionSaveParams {
  /** 会话类型：1岗位匹配 2简历优化 3模拟面试 4能力复盘 5自由问答 */
  sessionType: SessionType | number
  /** 处理的 Agent 名称（可选） */
  agentName?: string
  /** 会话标题，为空后端默认“新建会话” */
  title?: string
  /** 会话摘要（可选） */
  summary?: string
}

/**
 * 更新用户会话参数（对应后端 SessionUpdateDTO）
 *
 * 字段级更新约定：null/不传表示不修改。
 */
export interface SessionUpdateParams {
  /** 会话标题 */
  title?: string
  /** 会话摘要 */
  summary?: string
  /** 状态：1进行中 2已完成 */
  status?: SessionStatus | number
}

/** 会话记录分页查询参数（对应后端 SessionQueryDTO） */
export interface SessionPageParams {
  /** 当前页码，默认 1 */
  pageNum?: number
  /** 每页条数，默认 10，最大 100 */
  pageSize?: number
  /** 会话类型筛选：1-5 */
  sessionType?: SessionType | number
}

/* ============================ 模拟面试 ============================ */

/** 面试类型：1技术面 2HR面 */
export type InterviewType = 1 | 2

/** 面试难度：1简单 2中等 3困难 */
export type DifficultyLevel = 1 | 2 | 3

/** 面试状态：1进行中 2已完成 3已中断 */
export type InterviewStatus = 1 | 2 | 3

/** 面试消息角色 */
export type InterviewMessageRole = 'user' | 'assistant'

/** 面试消息类型：question 问题 / answer 回答 / evaluation 点评 */
export type InterviewMessageType = 'question' | 'answer' | 'evaluation'

/**
 * 面试对话消息（对应后端 InterviewMessageVO）
 */
export interface InterviewMessage {
  /** 消息 ID */
  id: number
  /** 所属面试记录 ID */
  interviewRecordId: number
  /** 消息角色：user/assistant */
  role: InterviewMessageRole | string
  /** 消息类型：question/answer/evaluation */
  messageType: InterviewMessageType | string
  /** 消息内容 */
  content: string
  /** 本条点评评分 0-100（可空） */
  score?: number
  /** 创建时间 */
  createTime?: string
}

/**
 * 模拟面试记录（对应后端 InterviewVO）
 *
 * messages 仅在详情接口组装返回，分页列表接口为 null/undefined。
 */
export interface InterviewRecord {
  /** 面试记录 ID */
  id: number
  /** 用户 ID */
  userId: number
  /** 面试类型：1技术面 2HR面 */
  interviewType: InterviewType | number
  /** 目标公司 */
  targetCompany?: string
  /** 目标岗位 */
  targetPosition?: string
  /** 难度：1简单 2中等 3困难 */
  difficultyLevel?: DifficultyLevel | number
  /** 关联简历记录 ID（resume_record.id，可选） */
  resumeId?: number
  /** 面试时长（秒） */
  durationSeconds?: number
  /** 提问数量 */
  questionCount?: number
  /** 综合评分 0-100 */
  overallScore?: number
  /** 面试复盘报告 */
  evaluationReport?: string
  /** 状态：1进行中 2已完成 3已中断 */
  status: InterviewStatus | number
  /** 创建时间 */
  createTime?: string
  /** 更新时间 */
  updateTime?: string
  /** 面试对话消息列表（仅详情接口返回） */
  messages?: InterviewMessage[]
}

/** 创建模拟面试参数（对应后端 InterviewCreateDTO） */
export interface InterviewCreateParams {
  /** 面试类型：1技术面 2HR面 */
  interviewType: InterviewType | number
  /** 目标公司（可选） */
  targetCompany?: string
  /** 目标岗位（可选） */
  targetPosition?: string
  /** 难度：1简单 2中等 3困难，默认 2 */
  difficultyLevel?: DifficultyLevel | number
  /** 关联简历记录 ID（可选，为空时由 AI 按通用题库提问） */
  resumeId?: number
}

/**
 * 更新模拟面试参数（对应后端 InterviewUpdateDTO，结束回填）
 *
 * 字段级更新约定：null/不传表示不修改。
 */
export interface InterviewUpdateParams {
  /** 面试时长（秒） */
  durationSeconds?: number
  /** 提问数量 */
  questionCount?: number
  /** 综合评分 0-100 */
  overallScore?: number
  /** 面试复盘报告 */
  evaluationReport?: string
  /** 状态：1进行中 2已完成 3已中断 */
  status?: InterviewStatus | number
}

/** 面试记录分页查询参数（对应后端 InterviewQueryDTO） */
export interface InterviewPageParams {
  /** 当前页码，默认 1 */
  pageNum?: number
  /** 每页条数，默认 10，最大 100 */
  pageSize?: number
  /** 面试类型筛选：1技术面 2HR面 */
  interviewType?: InterviewType | number
}

/**
 * 追加面试消息参数（对应后端 InterviewMessageDTO）
 *
 * 注意：后端 messageType 为必填（question/answer/evaluation），
 * 仅传 role/content 无法通过校验，故一并纳入；score 仅点评消息需要。
 */
export interface MessageAppendParams {
  /** 消息角色：user/assistant */
  role: InterviewMessageRole | string
  /** 消息类型：question/answer/evaluation */
  messageType: InterviewMessageType | string
  /** 消息内容 */
  content: string
  /** 本条点评评分 0-100（可选） */
  score?: number
}

/* ============================ 能力画像 ============================ */

/**
 * 能力维度（与面试复盘 Agent 写入的维度字符串保持一致）
 * 共 5 个维度：专业基础 / 工程实践 / 算法与数据结构 / 框架与中间件 / 软素养
 */
export const ABILITY_DIMENSIONS = [
  '专业基础',
  '工程实践',
  '算法与数据结构',
  '框架与中间件',
  '软素养',
] as const

/** 能力维度类型 */
export type AbilityDimension = (typeof ABILITY_DIMENSIONS)[number]

/**
 * 能力画像快照（对应后端 AbilityVO）
 */
export interface AbilityProfile {
  /** 快照 ID */
  id: number
  /** 用户 ID */
  userId: number
  /** 能力维度，见 ABILITY_DIMENSIONS */
  dimension: AbilityDimension | string
  /** 维度得分 0-100 */
  dimensionScore: number
  /** 维度评语 */
  evaluation?: string
  /** 快照日期（日期字符串） */
  snapshotDate?: string
  /** 创建时间 */
  createTime?: string
}

/**
 * 能力成长曲线数据点（对应后端 AbilityTrendVO）
 *
 * 不含 id/userId，仅用于绘制成长曲线。
 */
export interface AbilityTrendPoint {
  /** 能力维度 */
  dimension: AbilityDimension | string
  /** 维度得分 0-100 */
  dimensionScore: number
  /** 维度评语 */
  evaluation?: string
  /** 快照日期（日期字符串） */
  snapshotDate?: string
}

/* ============================ AI 对话转发 ============================ */

/**
 * AI 对话请求参数（对应 business AiChatDTO，由转发层从 JWT 注入 user_id）
 */
export interface AiChatParams {
  /** 业务侧会话标识（可选，AI 服务当前不落库，预留） */
  sessionId?: string
  /** 用户输入内容 */
  query: string
  /** 前端透传的简历文本（简历优化/面试场景，可选） */
  resumeText?: string
}

/**
 * AI 非流式对话结果（对应 business AiChatVO）
 *
 * 注意：非流式响应仅保证 agentName/finalResponse/error；
 * intent 字段在流式 meta 事件中必有，非流式可能不返回，故设为可选。
 */
export interface AiChatResult {
  /** 实际处理 Agent：job/resume/tech/hr/chat */
  agentName?: string
  /** 意图标识（非流式可能缺失） */
  intent?: string
  /** 完整回复内容（Markdown） */
  finalResponse?: string
  /** 错误信息，正常时为 null */
  error?: string | null
}
