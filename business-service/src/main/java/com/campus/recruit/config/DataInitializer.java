package com.campus.recruit.config;

import cn.hutool.crypto.digest.BCrypt;
import com.campus.recruit.entity.SysUser;
import com.campus.recruit.mapper.SysUserMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

/**
 * 启动数据初始化器
 *
 * <p>实现 {@link ApplicationRunner}，在应用启动完成后自动执行管理员账号初始化：</p>
 * <ul>
 *   <li>查询 sys_user 表总记录数（逻辑删除记录由 MyBatis-Plus 自动过滤）</li>
 *   <li>记录数为 0 时创建默认管理员账号：admin / 123456（BCrypt 加密入库）</li>
 *   <li>记录数大于 0 时跳过初始化，不执行任何写入</li>
 * </ul>
 *
 * <p>保证任何环境（本地 / 测试 / 生产）首次启动即有可登录账号。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DataInitializer implements ApplicationRunner {

    /** 默认管理员用户名 */
    private static final String DEFAULT_ADMIN_USERNAME = "admin";

    /** 默认管理员密码（仅初始化使用，建议首次登录后修改） */
    private static final String DEFAULT_ADMIN_PASSWORD = "123456";

    /** 默认管理员昵称 */
    private static final String DEFAULT_ADMIN_NICKNAME = "管理员";

    private final SysUserMapper sysUserMapper;

    /**
     * 应用启动完成后执行管理员账号初始化
     *
     * @param args 应用启动参数
     */
    @Override
    public void run(ApplicationArguments args) {
        // 查询用户总数（is_deleted=0 由 @TableLogic 自动过滤）
        Long count = sysUserMapper.selectCount(null);
        if (count != null && count > 0) {
            log.info("检测到已有用户，跳过管理员初始化");
            return;
        }

        SysUser admin = new SysUser();
        admin.setUsername(DEFAULT_ADMIN_USERNAME);
        admin.setPassword(BCrypt.hashpw(DEFAULT_ADMIN_PASSWORD));
        admin.setNickname(DEFAULT_ADMIN_NICKNAME);
        admin.setEmail("");
        admin.setPhone("");
        admin.setAvatar("");
        admin.setStatus(1);
        sysUserMapper.insert(admin);

        log.info("初始化管理员账号: username={}", admin.getUsername());
    }
}
