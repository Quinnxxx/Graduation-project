package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.dto.LoginDTO;
import com.campus.recruit.dto.PasswordUpdateDTO;
import com.campus.recruit.dto.RegisterDTO;
import com.campus.recruit.dto.SysUserQueryDTO;
import com.campus.recruit.dto.UserUpdateDTO;
import com.campus.recruit.entity.SysUser;
import com.campus.recruit.vo.LoginVO;
import com.campus.recruit.vo.SysUserVO;

/**
 * 系统用户服务接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface SysUserService extends IService<SysUser> {

    /**
     * 用户登录
     *
     * @param loginDTO 登录参数
     * @return 登录结果（Token + 用户信息）
     */
    LoginVO login(LoginDTO loginDTO);

    /**
     * 用户注册
     *
     * @param registerDTO 注册参数
     */
    void register(RegisterDTO registerDTO);

    /**
     * 分页查询用户
     *
     * @param queryDTO 分页查询参数
     * @return 分页结果
     */
    PageResult<SysUserVO> pageQuery(SysUserQueryDTO queryDTO);

    /**
     * 根据 ID 查询用户
     *
     * @param id 用户 ID
     * @return 用户信息
     */
    SysUserVO getUserById(Long id);

    /**
     * 更新用户信息
     *
     * @param id        用户 ID
     * @param updateDTO 更新参数
     */
    void updateUser(Long id, UserUpdateDTO updateDTO);

    /**
     * 删除用户（逻辑删除）
     *
     * @param id 用户 ID
     */
    void deleteUser(Long id);

    /**
     * 获取当前登录用户信息
     *
     * @param userId 当前登录用户 ID
     * @return 用户信息
     */
    SysUserVO getCurrentUser(Long userId);

    /**
     * 修改当前用户密码
     *
     * @param userId 当前登录用户 ID
     * @param dto    修改密码参数
     */
    void changePassword(Long userId, PasswordUpdateDTO dto);
}
