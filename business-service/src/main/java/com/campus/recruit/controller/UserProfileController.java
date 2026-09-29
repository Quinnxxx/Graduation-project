package com.campus.recruit.controller;

import com.campus.recruit.common.Result;
import com.campus.recruit.config.JwtAuthInterceptor;
import com.campus.recruit.dto.UserProfileSaveDTO;
import com.campus.recruit.service.UserProfileService;
import com.campus.recruit.vo.UserProfileVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户求职画像接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "用户画像", description = "用户求职画像查询与维护")
@RestController
@RequiredArgsConstructor
@Validated
public class UserProfileController {

    private final UserProfileService userProfileService;

    /**
     * 获取当前用户求职画像
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @return 用户画像视图对象，未填写时 data 为 null
     */
    @Operation(summary = "获取当前用户画像")
    @GetMapping("/profile/me")
    public Result<UserProfileVO> getMyProfile(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(userProfileService.getByUserId(userId));
    }

    /**
     * 创建或更新当前用户求职画像（按 userId 幂等 upsert）
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @param dto     画像保存参数
     * @return 保存后的用户画像视图对象
     */
    @Operation(summary = "创建或更新当前用户画像")
    @PostMapping("/profile/me")
    public Result<UserProfileVO> saveMyProfile(HttpServletRequest request, @Valid @RequestBody UserProfileSaveDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(userProfileService.saveOrUpdate(userId, dto));
    }
}
