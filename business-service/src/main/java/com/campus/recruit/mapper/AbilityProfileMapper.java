package com.campus.recruit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.recruit.entity.AbilityProfile;
import org.apache.ibatis.annotations.Mapper;

/**
 * 能力画像快照 Mapper
 *
 * <p>继承 {@link BaseMapper} 获得基础 CRUD 能力。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Mapper
public interface AbilityProfileMapper extends BaseMapper<AbilityProfile> {
}
