package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.dto.JobPositionQueryDTO;
import com.campus.recruit.entity.JobPosition;
import com.campus.recruit.vo.JobPositionVO;
import com.campus.recruit.vo.JobStatsVO;

/**
 * 校招岗位服务接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface JobPositionService extends IService<JobPosition> {

    /**
     * 分页查询校招岗位（多条件筛选）
     *
     * @param dto 分页查询参数
     * @return 分页结果
     */
    PageResult<JobPositionVO> pageQuery(JobPositionQueryDTO dto);

    /**
     * 查询岗位详情
     *
     * @param id 岗位 ID
     * @return 岗位完整信息
     */
    JobPositionVO getDetail(Long id);

    /**
     * 校招岗位统计（仅统计在招岗位）
     *
     * @return 统计结果（总数、类别分布、城市 Top10）
     */
    JobStatsVO getStats();
}
