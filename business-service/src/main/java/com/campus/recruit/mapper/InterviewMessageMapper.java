package com.campus.recruit.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.campus.recruit.entity.InterviewMessage;
import org.apache.ibatis.annotations.Mapper;

/**
 * 面试消息 Mapper
 *
 * <p>继承 {@link BaseMapper} 获得基础 CRUD 能力，消息表无逻辑删除字段，删除为物理删除。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Mapper
public interface InterviewMessageMapper extends BaseMapper<InterviewMessage> {
}
