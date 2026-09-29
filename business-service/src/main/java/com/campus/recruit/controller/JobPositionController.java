package com.campus.recruit.controller;

import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.Result;
import com.campus.recruit.dto.JobPositionQueryDTO;
import com.campus.recruit.service.JobPositionService;
import com.campus.recruit.vo.JobPositionVO;
import com.campus.recruit.vo.JobStatsVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

/**
 * 校招岗位查询接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "校招岗位", description = "校招岗位查询与统计（数据由采集Agent写入）")
@RestController
@RequiredArgsConstructor
@Validated
public class JobPositionController {

    private final JobPositionService jobPositionService;

    /**
     * 分页查询校招岗位
     *
     * @param dto 分页查询参数（GET 查询参数）
     * @return 分页结果
     */
    @Operation(summary = "分页查询校招岗位")
    @GetMapping("/jobs/page")
    public Result<PageResult<JobPositionVO>> page(@Valid JobPositionQueryDTO dto) {
        return Result.success(jobPositionService.pageQuery(dto));
    }

    /**
     * 查询岗位详情
     *
     * @param id 岗位 ID
     * @return 岗位完整信息
     */
    @Operation(summary = "查询岗位详情")
    @GetMapping("/jobs/{id}")
    public Result<JobPositionVO> detail(@PathVariable("id") Long id) {
        return Result.success(jobPositionService.getDetail(id));
    }

    /**
     * 校招岗位统计
     *
     * @return 统计结果（在招总数、类别分布、城市 Top10）
     */
    @Operation(summary = "校招岗位统计")
    @GetMapping("/jobs/stats")
    public Result<JobStatsVO> stats() {
        return Result.success(jobPositionService.getStats());
    }
}
