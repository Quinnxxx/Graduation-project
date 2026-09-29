package com.campus.recruit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.recruit.entity.UserProfile;
import org.apache.ibatis.annotations.Mapper;

/**
 * 用户求职画像 Mapper
 *
 * <p>继承 {@link BaseMapper} 获得基础 CRUD 能力，复杂 SQL 可在此扩展 XML 或注解方法。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Mapper
public interface UserProfileMapper extends BaseMapper<UserProfile> {
}
