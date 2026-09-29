package com.campus.recruit.controller;

import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.Result;
import com.campus.recruit.config.JwtAuthInterceptor;
import com.campus.recruit.dto.LoginDTO;
import com.campus.recruit.dto.PasswordUpdateDTO;
import com.campus.recruit.dto.RegisterDTO;
import com.campus.recruit.dto.SysUserQueryDTO;
import com.campus.recruit.dto.UserUpdateDTO;
import com.campus.recruit.service.SysUserService;
import com.campus.recruit.vo.LoginVO;
import com.campus.recruit.vo.SysUserVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * 用户认证与信息管理接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Tag(name = "用户管理", description = "用户认证与信息管理")
@RestController
@RequiredArgsConstructor
@Validated
public class SysUserController {

    private final SysUserService sysUserService;

    /**
     * 用户登录
     *
     * @param loginDTO 登录参数
     * @return 登录结果
     */
    @Operation(summary = "用户登录")
    @PostMapping("/auth/login")
    public Result<LoginVO> login(@Valid @RequestBody LoginDTO loginDTO) {
        return Result.success(sysUserService.login(loginDTO));
    }

    /**
     * 用户注册
     *
     * @param registerDTO 注册参数
     * @return 操作结果
     */
    @Operation(summary = "用户注册")
    @PostMapping("/auth/register")
    public Result<Void> register(@Valid @RequestBody RegisterDTO registerDTO) {
        sysUserService.register(registerDTO);
        return Result.success();
    }

    /**
     * 获取当前登录用户信息（需携带 Token）
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @return 当前用户信息
     */
    @Operation(summary = "获取当前登录用户信息")
    @GetMapping("/users/me")
    public Result<SysUserVO> me(HttpServletRequest request) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        return Result.success(sysUserService.getCurrentUser(userId));
    }

    /**
     * 修改当前用户密码（需携带 Token）
     *
     * @param request 请求对象（用户信息由拦截器写入）
     * @param dto     修改密码参数
     * @return 操作结果
     */
    @Operation(summary = "修改当前用户密码")
    @PutMapping("/users/me/password")
    public Result<Void> changePassword(HttpServletRequest request, @Valid @RequestBody PasswordUpdateDTO dto) {
        Long userId = (Long) request.getAttribute(JwtAuthInterceptor.ATTR_USER_ID);
        sysUserService.changePassword(userId, dto);
        return Result.success();
    }

    /**
     * 分页查询用户
     *
     * @param queryDTO 分页查询参数
     * @return 分页结果
     */
    @Operation(summary = "分页查询用户")
    @GetMapping("/users/page")
    public Result<PageResult<SysUserVO>> page(@Valid SysUserQueryDTO queryDTO) {
        return Result.success(sysUserService.pageQuery(queryDTO));
    }

    /**
     * 根据 ID 查询用户
     *
     * @param id 用户 ID
     * @return 用户信息
     */
    @Operation(summary = "根据ID查询用户")
    @GetMapping("/users/{id}")
    public Result<SysUserVO> getById(@PathVariable("id") Long id) {
        return Result.success(sysUserService.getUserById(id));
    }

    /**
     * 更新用户信息
     *
     * @param id        用户 ID
     * @param updateDTO 更新参数
     * @return 操作结果
     */
    @Operation(summary = "更新用户信息")
    @PutMapping("/users/{id}")
    public Result<Void> update(@PathVariable("id") Long id, @Valid @RequestBody UserUpdateDTO updateDTO) {
        sysUserService.updateUser(id, updateDTO);
        return Result.success();
    }

    /**
     * 删除用户（逻辑删除）
     *
     * @param id 用户 ID
     * @return 操作结果
     */
    @Operation(summary = "删除用户（逻辑删除）")
    @DeleteMapping("/users/{id}")
    public Result<Void> delete(@PathVariable("id") Long id) {
        sysUserService.deleteUser(id);
        return Result.success();
    }
}
