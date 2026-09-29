package com.campus.recruit.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.io.Serializable;
import java.util.List;

/**
 * 内部批量岗位入库请求
 *
 * <p>采集链路唯一写入口，一次请求 1-200 条，逐条按 {@code job_hash} 幂等
 * （已存在跳过，不影响其它记录）。仅允许携带正确内部令牌的调用方访问。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "内部批量岗位入库请求")
public class InternalJobBatchDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 岗位条目列表（1-200 条） */
    @Schema(description = "岗位条目列表（1-200条）")
    @NotNull(message = "岗位列表不能为空")
    @Size(min = 1, max = 200, message = "单批岗位数量须在1-200之间")
    @Valid
    private List<InternalJobItemDTO> items;
}