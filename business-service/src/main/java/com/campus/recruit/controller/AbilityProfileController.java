package com.campus.recruit.controller;

import com.campus.recruit.common.Result;
import com.campus.recruit.config.JwtAuthInterceptor;
import com.campus.recruit.dto.AbilitySaveDTO;
import com.campus.recruit.service.AbilityProfileService;
import com.campus.recruit.vo.AbilityTrendVO;
import com.campus.recruit.vo.AbilityVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 能力画像接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "能力画像", description = "能力画像快照查询与写入")
@RestController
@RequiredArgsConstructor
@Validated
public class AbilityProfileController {

    private final AbilityProfileService abilityProfileService;

    /**
     * 查询我的最新能力画像（各维度最新快照）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @return 各维度最新快照列表
     */
    @Operation(summary = "查询我的最新能力画像(各维度)")
    @GetMapping("/abilities/mine")
    public Result<List<AbilityVO>> mine(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(abilityProfileService.getLatest(userId));
    }

    /**
     * 查询能力成长曲线
     *
     * @param request   HTTP 请求（获取当前用户 ID）
     * @param dimension 能力维度（必填）
     * @return 成长曲线数据点列表
     */
    @Operation(summary = "查询能力成长曲线")
    @GetMapping("/abilities/trend")
    public Result<List<AbilityTrendVO>> trend(HttpServletRequest request,
                                              @RequestParam("dimension") String dimension) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(abilityProfileService.getTrend(userId, dimension));
    }

    /**
     * 写入能力画像快照（供面试复盘 Agent 调用）
     *
     * @param request HTTP 请求（获取当前用户 ID）
     * @param dto     快照参数
     * @return 快照视图对象
     */
    @Operation(summary = "写入能力画像快照(供面试复盘Agent调用)")
    @PostMapping("/abilities")
    public Result<AbilityVO> save(HttpServletRequest request, @Valid @RequestBody AbilitySaveDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(abilityProfileService.save(userId, dto));
    }
}
