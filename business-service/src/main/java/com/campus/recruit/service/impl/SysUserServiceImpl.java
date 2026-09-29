package com.campus.recruit.service.impl;

import cn.hutool.crypto.digest.BCrypt;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.LoginDTO;
import com.campus.recruit.dto.PasswordUpdateDTO;
import com.campus.recruit.dto.RegisterDTO;
import com.campus.recruit.dto.SysUserQueryDTO;
import com.campus.recruit.dto.UserUpdateDTO;
import com.campus.recruit.entity.SysUser;
import com.campus.recruit.exception.BusinessException;
import com.campus.recruit.mapper.SysUserMapper;
import com.campus.recruit.service.SysUserService;
import com.campus.recruit.utils.JwtUtil;
import com.campus.recruit.vo.LoginVO;
import com.campus.recruit.vo.SysUserVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

/**
 * 系统用户服务实现
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SysUserServiceImpl extends ServiceImpl<SysUserMapper, SysUser> implements SysUserService {

    private final JwtUtil jwtUtil;

    /**
     * 用户登录：校验账号密码与状态，签发 JWT
     *
     * @param loginDTO 登录参数
     * @return 登录结果（Token + 用户信息）
     */
    @Override
    public LoginVO login(LoginDTO loginDTO) {
        SysUser user = lambdaQuery()
                .eq(SysUser::getUsername, loginDTO.getUsername())
                .one();
        // 二次校验：账号不存在与密码错误统一提示，避免账号枚举
        if (user == null) {
            throw new BusinessException(ResultCode.USERNAME_OR_PASSWORD_ERROR);
        }
        if (!BCrypt.checkpw(loginDTO.getPassword(), user.getPassword())) {
            throw new BusinessException(ResultCode.USERNAME_OR_PASSWORD_ERROR);
        }
        // 二次校验：账号状态
        if (user.getStatus() != null && user.getStatus() == 0) {
            throw new BusinessException(ResultCode.USER_DISABLED);
        }
        // 更新最近登录时间
        SysUser update = new SysUser();
        update.setId(user.getId());
        update.setLastLoginTime(LocalDateTime.now());
        updateById(update);

        String token = jwtUtil.generateToken(user.getId(), user.getUsername());
        LoginVO loginVO = new LoginVO();
        loginVO.setToken(token);
        loginVO.setTokenType("Bearer");
        loginVO.setExpiresIn(jwtUtil.getExpiration());
        loginVO.setUser(toVO(user));
        return loginVO;
    }

    /**
     * 用户注册：校验唯一性与密码一致性，BCrypt 加密后入库
     *
     * @param registerDTO 注册参数
     */
    @Override
    public void register(RegisterDTO registerDTO) {
        // 二次校验：两次密码必须一致
        if (!registerDTO.getPassword().equals(registerDTO.getConfirmPassword())) {
            throw new BusinessException(ResultCode.PASSWORD_NOT_MATCH);
        }
        // 二次校验：用户名唯一
        Long count = lambdaQuery()
                .eq(SysUser::getUsername, registerDTO.getUsername())
                .count();
        if (count > 0) {
            throw new BusinessException(ResultCode.USERNAME_EXISTS);
        }
        SysUser user = new SysUser();
        BeanUtils.copyProperties(registerDTO, user);
        user.setPassword(BCrypt.hashpw(registerDTO.getPassword()));
        user.setStatus(1);
        user.setAvatar("");
        save(user);
        log.info("用户注册成功: username={}", registerDTO.getUsername());
    }

    /**
     * 分页查询用户（支持用户名模糊与状态过滤）
     *
     * @param queryDTO 分页查询参数
     * @return 分页结果
     */
    @Override
    public PageResult<SysUserVO> pageQuery(SysUserQueryDTO queryDTO) {
        LambdaQueryWrapper<SysUser> wrapper = new LambdaQueryWrapper<>();
        wrapper.like(StringUtils.isNotBlank(queryDTO.getUsername()), SysUser::getUsername, queryDTO.getUsername())
                .eq(queryDTO.getStatus() != null, SysUser::getStatus, queryDTO.getStatus())
                .orderByDesc(SysUser::getCreateTime);
        Page<SysUser> page = page(new Page<>(queryDTO.getPageNum(), queryDTO.getPageSize()), wrapper);
        List<SysUserVO> records = page.getRecords().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
        return PageResult.of(records, page.getTotal(), (long) queryDTO.getPageNum(), (long) queryDTO.getPageSize());
    }

    /**
     * 根据 ID 查询用户
     *
     * @param id 用户 ID
     * @return 用户信息
     */
    @Override
    public SysUserVO getUserById(Long id) {
        // 二次校验：ID 非空
        if (id == null) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "用户ID不能为空");
        }
        SysUser user = getById(id);
        if (user == null) {
            throw new BusinessException(ResultCode.USER_NOT_EXIST);
        }
        return toVO(user);
    }

    /**
     * 更新用户信息
     *
     * @param id        用户 ID
     * @param updateDTO 更新参数
     */
    @Override
    public void updateUser(Long id, UserUpdateDTO updateDTO) {
        // 二次校验：ID 非空且用户存在
        if (id == null) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "用户ID不能为空");
        }
        if (getById(id) == null) {
            throw new BusinessException(ResultCode.USER_NOT_EXIST);
        }
        SysUser update = new SysUser();
        BeanUtils.copyProperties(updateDTO, update);
        update.setId(id);
        updateById(update);
    }

    /**
     * 删除用户（逻辑删除）
     *
     * @param id 用户 ID
     */
    @Override
    public void deleteUser(Long id) {
        // 二次校验：ID 非空且用户存在
        if (id == null) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "用户ID不能为空");
        }
        if (getById(id) == null) {
            throw new BusinessException(ResultCode.USER_NOT_EXIST);
        }
        removeById(id);
    }

    /**
     * 获取当前登录用户信息
     *
     * @param userId 当前登录用户 ID
     * @return 用户信息
     */
    @Override
    public SysUserVO getCurrentUser(Long userId) {
        return getUserById(userId);
    }

    /**
     * 修改当前用户密码：校验旧密码与两次新密码一致后更新
     *
     * @param userId 当前登录用户 ID
     * @param dto    修改密码参数
     */
    @Override
    public void changePassword(Long userId, PasswordUpdateDTO dto) {
        // 二次校验：用户必须存在
        SysUser user = getById(userId);
        if (user == null) {
            throw new BusinessException(ResultCode.USER_NOT_EXIST);
        }
        // 二次校验：旧密码必须正确
        if (!BCrypt.checkpw(dto.getOldPassword(), user.getPassword())) {
            throw new BusinessException(ResultCode.OLD_PASSWORD_ERROR);
        }
        // 二次校验：两次输入的新密码必须一致
        if (!dto.getNewPassword().equals(dto.getConfirmPassword())) {
            throw new BusinessException(ResultCode.PASSWORD_NOT_MATCH);
        }
        // 只更新密码字段，避免误改其他属性
        SysUser update = new SysUser();
        update.setId(userId);
        update.setPassword(BCrypt.hashpw(dto.getNewPassword()));
        updateById(update);
        log.info("用户修改密码成功: userId={}", userId);
    }

    /**
     * 实体转视图对象（剔除敏感字段）
     *
     * @param user 用户实体
     * @return 用户视图对象
     */
    private SysUserVO toVO(SysUser user) {
        SysUserVO vo = new SysUserVO();
        BeanUtils.copyProperties(user, vo);
        return vo;
    }
}
