package com.campus.recruit.controller;

import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.Result;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.AbilitySaveDTO;
import com.campus.recruit.dto.InternalAbilitySaveDTO;
import com.campus.recruit.dto.InternalResumeCreateDTO;
import com.campus.recruit.dto.InternalResumeUpdateDTO;
import com.campus.recruit.dto.ResumeQueryDTO;
import com.campus.recruit.dto.ResumeSaveDTO;
import com.campus.recruit.dto.ResumeUpdateDTO;
import com.campus.recruit.service.AbilityProfileService;
import com.campus.recruit.service.ResumeRecordService;
import com.campus.recruit.service.UserProfileService;
import com.campus.recruit.vo.AbilityVO;
import com.campus.recruit.vo.ResumeVO;
import com.campus.recruit.vo.UserProfileVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

/**
 * 内部用户数据接口
 *
 * <p>为 AI Agent 服务提供用户数据读写能力，由
 * {@link com.campus.recruit.config.InternalTokenInterceptor} 统一校验
 * {@code X-Internal-Token} 请求头。</p>
 *
 * <p>userId 由请求参数/请求体显式传入（AI 侧从图状态透传，源头为 JWT 解析的
 * 真实用户 id），本控制器不自行解析 JWT。</p>
 *
 * @author campus-recruit
 * @since 1.1.0
 */
@Slf4j
@Tag(name = "内部用户数据接口", description = "系统内部接口，仅 AI 服务调用")
@RestController
@RequiredArgsConstructor
@Validated
@RequestMapping("/internal")
public class InternalUserController {

    private final UserProfileService userProfileService;
    private final ResumeRecordService resumeRecordService;
    private final AbilityProfileService abilityProfileService;

    /**
     * 获取用户求职画像
     *
     * @param userId 用户 ID
     * @return 画像视图对象，无画像时 data=null
     */
    @Operation(summary = "获取用户求职画像")
    @GetMapping("/profile")
    public Result<UserProfileVO> getProfile(
            @RequestParam @NotNull @Positive(message = "userId 必须为正整数") Long userId) {
        UserProfileVO profile = userProfileService.getByUserId(userId);
        return Result.success(profile);
    }

    /**
     * 获取用户最新简历
     *
     * @param userId 用户 ID
     * @return 最新简历视图对象，无记录时 data=null
     */
    @Operation(summary = "获取用户最新简历")
    @GetMapping("/resumes/latest")
    public Result<ResumeVO> getLatestResume(
            @RequestParam @NotNull @Positive(message = "userId 必须为正整数") Long userId) {
        // 使用分页查询取第一条（按更新时间倒序）
        ResumeQueryDTO queryDTO = new ResumeQueryDTO();
        queryDTO.setPageNum(1);
        queryDTO.setPageSize(1);
        
        PageResult<ResumeVO> pageResult = resumeRecordService.pageQuery(userId, queryDTO);
        
        if (pageResult.getList() != null && !pageResult.getList().isEmpty()) {
            return Result.success(pageResult.getList().get(0));
        }
        return Result.success(null);
    }

    /**
     * 创建简历记录
     *
     * @param dto 创建参数（含 userId）
     * @return 创建后的简历视图对象
     */
    @Operation(summary = "创建简历记录")
    @PostMapping("/resumes")
    public Result<ResumeVO> createResume(@Valid @RequestBody InternalResumeCreateDTO dto) {
        // 转换为 ResumeSaveDTO
        ResumeSaveDTO saveDTO = new ResumeSaveDTO();
        saveDTO.setResumeTitle(dto.getResumeTitle());
        saveDTO.setOriginalContent(dto.getOriginalContent());
        saveDTO.setTargetPositionName(dto.getTargetPositionName());
        
        ResumeVO resume = resumeRecordService.create(dto.getUserId(), saveDTO);
        
        log.info("内部接口创建简历: userId={}, resumeId={}, titleLen={}", 
                dto.getUserId(), resume.getId(), 
                dto.getResumeTitle() != null ? dto.getResumeTitle().length() : 0);
        
        return Result.success(resume);
    }

    /**
     * 更新简历记录
     *
     * <p>校验记录归属 userId，防止越权操作。</p>
     *
     * @param id  简历记录 ID
     * @param dto 更新参数（含 userId，用于归属校验）
     * @return 更新后的简历视图对象
     */
    @Operation(summary = "更新简历记录")
    @PutMapping("/resumes/{id}")
    public Result<ResumeVO> updateResume(
            @PathVariable @NotNull @Positive(message = "id 必须为正整数") Long id,
            @Valid @RequestBody InternalResumeUpdateDTO dto) {
        // 转换为 ResumeUpdateDTO
        ResumeUpdateDTO updateDTO = new ResumeUpdateDTO();
        updateDTO.setOptimizedContent(dto.getOptimizedContent());
        updateDTO.setOptimizationSuggestions(dto.getOptimizationSuggestions());
        updateDTO.setResumeScore(dto.getResumeScore());
        updateDTO.setOptimizedScore(dto.getOptimizedScore());
        updateDTO.setStatus(dto.getStatus());
        
        // service.update 内部校验记录归属 userId
        ResumeVO resume = resumeRecordService.update(dto.getUserId(), id, updateDTO);
        
        log.info("内部接口更新简历: userId={}, resumeId={}, contentLen={}", 
                dto.getUserId(), id, 
                dto.getOptimizedContent() != null ? dto.getOptimizedContent().length() : 0);
        
        return Result.success(resume);
    }

    /**
     * 写入能力画像快照
     *
     * @param dto 快照参数（含 userId）
     * @return 快照视图对象
     */
    @Operation(summary = "写入能力画像快照")
    @PostMapping("/abilities")
    public Result<AbilityVO> saveAbility(@Valid @RequestBody InternalAbilitySaveDTO dto) {
        // 转换为 AbilitySaveDTO
        AbilitySaveDTO saveDTO = new AbilitySaveDTO();
        saveDTO.setDimension(dto.getDimension());
        saveDTO.setDimensionScore(dto.getDimensionScore());
        saveDTO.setEvaluation(dto.getEvaluation());
        saveDTO.setSnapshotDate(dto.getSnapshotDate());
        
        AbilityVO ability = abilityProfileService.save(dto.getUserId(), saveDTO);
        
        log.info("内部接口写入能力快照: userId={}, dimension={}, score={}", 
                dto.getUserId(), dto.getDimension(), dto.getDimensionScore());
        
        return Result.success(ability);
    }

    /**
     * 获取用户各维度最新能力画像
     *
     * <p>复用 {@link AbilityProfileService#getLatest(Long)}：按快照日期倒序、
     * 维度分组取每个维度的最新一条，通常返回 5 个维度。无记录时 data=null。</p>
     *
     * @param userId 用户 ID
     * @return 各维度最新能力快照列表，无记录时 data=null
     */
    @Operation(summary = "获取用户各维度最新能力画像")
    @GetMapping("/abilities/latest")
    public Result<List<AbilityVO>> getLatestAbility(
            @RequestParam @NotNull @Positive(message = "userId 必须为正整数") Long userId) {
        List<AbilityVO> abilities = abilityProfileService.getLatest(userId);
        if (abilities == null || abilities.isEmpty()) {
            return Result.success(null);
        }
        return Result.success(abilities);
    }
}
