package com.campus.recruit.vo;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

/**
 * 内部批量岗位入库结果
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "内部批量岗位入库结果")
public class InternalImportVO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 本次新建条数（job_hash 唯一键未命中） */
    @Schema(description = "本次新建条数")
    private int created = 0;

    /** 本次跳过条数（job_hash 已存在，含唯一键并发冲突） */
    @Schema(description = "本次跳过条数")
    private int skipped = 0;

    /** 本次失败条数（除重复外的写入异常，明细见服务日志） */
    @Schema(description = "本次失败条数")
    private int failed = 0;
}