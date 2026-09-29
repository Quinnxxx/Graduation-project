package com.campus.recruit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.recruit.entity.ResumeRecord;
import org.apache.ibatis.annotations.Mapper;

/**
 * 简历优化记录 Mapper
 *
 * <p>继承 {@link BaseMapper} 获得基础 CRUD 能力。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Mapper
public interface ResumeRecordMapper extends BaseMapper<ResumeRecord> {
}
