package com.campus.recruit.controller;

import com.campus.recruit.common.Result;
import com.campus.recruit.dto.InternalJobBatchDTO;
import com.campus.recruit.service.InternalJobService;
import com.campus.recruit.vo.InternalImportVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * 内部岗位采集入库接口
 *
 * <p>采集链路唯一写入口：由 {@link com.campus.recruit.config.InternalTokenInterceptor}
 * 统一校验 {@code X-Internal-Token} 请求头，缺失 / 错误令牌返回 HTTP 401。
 * 本接口不经过用户 JWT 鉴权（由采集 Agent 系统调用）。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "内部采集接口", description = "系统内部接口，仅 AI 服务调用")
@RestController
@RequiredArgsConstructor
@Validated
@RequestMapping("/internal/jobs")
public class InternalJobController {

    private final InternalJobService internalJobService;

    /**
     * 批量导入岗位记录（逐条幂等，1-200 条）
     *
     * @param dto 批量岗位请求
     * @return 入库结果（新建/跳过/失败计数）
     */
    @Operation(summary = "批量导入岗位记录（内部令牌）")
    @PostMapping("/batch")
    public Result<InternalImportVO> importBatch(@Valid @RequestBody InternalJobBatchDTO dto) {
        return Result.success(internalJobService.importBatch(dto));
    }
}