package com.campus.recruit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.recruit.entity.SysUser;
import org.apache.ibatis.annotations.Mapper;

/**
 * 系统用户 Mapper
 *
 * <p>继承 {@link BaseMapper} 获得基础 CRUD 能力，复杂 SQL 可在此扩展 XML 或注解方法。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Mapper
public interface SysUserMapper extends BaseMapper<SysUser> {
}
