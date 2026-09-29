package com.campus.recruit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.recruit.entity.JobPosition;
import org.apache.ibatis.annotations.Mapper;

/**
 * 校招岗位 Mapper
 *
 * <p>继承 {@link BaseMapper} 获得基础查询能力，岗位数据由采集 Agent 写入，本模块只读。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Mapper
public interface JobPositionMapper extends BaseMapper<JobPosition> {
}
