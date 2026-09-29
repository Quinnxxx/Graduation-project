package com.campus.recruit.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.JobPositionQueryDTO;
import com.campus.recruit.entity.JobPosition;
import com.campus.recruit.exception.BusinessException;
import com.campus.recruit.mapper.JobPositionMapper;
import com.campus.recruit.service.JobPositionService;
import com.campus.recruit.vo.JobPositionVO;
import com.campus.recruit.vo.JobStatsVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 校招岗位服务实现
 *
 * <p>岗位数据由后台采集 Agent 写入，本模块仅提供查询与统计，不做增删改。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class JobPositionServiceImpl extends ServiceImpl<JobPositionMapper, JobPosition> implements JobPositionService {

    /** 统计分组中空值归入的默认名称 */
    private static final String UNCLASSIFIED = "未分类";

    /**
     * 分页查询校招岗位（多条件筛选，仅对非空条件生效）
     *
     * @param dto 分页查询参数
     * @return 分页结果
     */
    @Override
    public PageResult<JobPositionVO> pageQuery(JobPositionQueryDTO dto) {
        LambdaQueryWrapper<JobPosition> wrapper = new LambdaQueryWrapper<>();
        // 关键词：岗位名称 / 公司名称 / 岗位职责 / 任职要求 任一模糊命中
        if (StringUtils.isNotBlank(dto.getKeyword())) {
            String keyword = dto.getKeyword();
            wrapper.and(w -> w.like(JobPosition::getPositionName, keyword)
                    .or().like(JobPosition::getCompanyName, keyword)
                    .or().like(JobPosition::getJobDescription, keyword)
                    .or().like(JobPosition::getJobRequirement, keyword));
        }
        // 公司名称模糊匹配
        wrapper.like(StringUtils.isNotBlank(dto.getCompanyName()), JobPosition::getCompanyName, dto.getCompanyName());
        // 精确匹配条件
        wrapper.eq(StringUtils.isNotBlank(dto.getJobCategory()), JobPosition::getJobCategory, dto.getJobCategory());
        wrapper.eq(StringUtils.isNotBlank(dto.getWorkCity()), JobPosition::getWorkCity, dto.getWorkCity());
        wrapper.eq(StringUtils.isNotBlank(dto.getIndustry()), JobPosition::getIndustry, dto.getIndustry());
        wrapper.eq(dto.getEducationRequirement() != null, JobPosition::getEducationRequirement, dto.getEducationRequirement());
        // 状态不传时查询全部
        wrapper.eq(dto.getStatus() != null, JobPosition::getStatus, dto.getStatus());
        // 薪资区间交叉：岗位薪资上限 >= 期望下限，且岗位薪资下限 <= 期望上限
        wrapper.ge(dto.getSalaryMin() != null, JobPosition::getSalaryMax, dto.getSalaryMin());
        wrapper.le(dto.getSalaryMax() != null, JobPosition::getSalaryMin, dto.getSalaryMax());
        // 按发布时间倒序，同时间按 ID 倒序
        wrapper.orderByDesc(JobPosition::getPublishTime).orderByDesc(JobPosition::getId);

        Page<JobPosition> page = page(new Page<>(dto.getPageNum(), dto.getPageSize()), wrapper);
        List<JobPositionVO> records = page.getRecords().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
        return PageResult.of(records, page.getTotal(), (long) dto.getPageNum(), (long) dto.getPageSize());
    }

    /**
     * 查询岗位详情
     *
     * @param id 岗位 ID
     * @return 岗位完整信息
     */
    @Override
    public JobPositionVO getDetail(Long id) {
        // 二次校验：ID 非空
        if (id == null) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "岗位ID不能为空");
        }
        JobPosition entity = getById(id);
        if (entity == null) {
            throw new BusinessException(ResultCode.JOB_POSITION_NOT_EXIST);
        }
        return toVO(entity);
    }

    /**
     * 校招岗位统计（仅统计 status=1 的在招岗位）
     *
     * @return 统计结果（在招总数、类别分布、城市 Top10）
     */
    @Override
    public JobStatsVO getStats() {
        JobStatsVO stats = new JobStatsVO();
        // 在招岗位总数（is_deleted=0 由 @TableLogic 自动过滤）
        stats.setTotalCount(lambdaQuery()
                .eq(JobPosition::getStatus, 1)
                .count());

        // 按岗位类别分组计数
        List<JobStatsVO.NameCountVO> categoryCounts = groupCount("job_category");
        stats.setCategoryCounts(categoryCounts);

        // 按城市分组计数，只取前 10
        List<JobStatsVO.NameCountVO> cityCounts = groupCount("work_city");
        stats.setCityCounts(cityCounts.stream().limit(10).collect(Collectors.toList()));

        log.info("校招岗位统计完成: totalCount={}, categorySize={}, citySize={}",
                stats.getTotalCount(), categoryCounts.size(), cityCounts.size());
        return stats;
    }

    /**
     * 按指定字段分组统计在招岗位数量
     *
     * <p>空值或空串分组归入"未分类"。</p>
     *
     * @param column 分组字段（job_category / work_city）
     * @return 统计列表，按数量倒序
     */
    private List<JobStatsVO.NameCountVO> groupCount(String column) {
        QueryWrapper<JobPosition> wrapper = new QueryWrapper<>();
        wrapper.select(column + " AS name", "COUNT(*) AS count")
                .eq("status", 1)
                .groupBy(column)
                .orderByDesc("count");
        List<Map<String, Object>> maps = baseMapper.selectMaps(wrapper);
        List<JobStatsVO.NameCountVO> result = new ArrayList<>();
        for (Map<String, Object> map : maps) {
            JobStatsVO.NameCountVO item = new JobStatsVO.NameCountVO();
            Object name = map.get("name");
            // 空值分组归入"未分类"
            item.setName(name == null || StringUtils.isBlank(name.toString()) ? UNCLASSIFIED : name.toString());
            Object count = map.get("count");
            item.setCount(count == null ? 0L : ((Number) count).longValue());
            result.add(item);
        }
        return result;
    }

    /**
     * 实体转视图对象
     *
     * @param entity 校招岗位实体
     * @return 校招岗位视图对象
     */
    private JobPositionVO toVO(JobPosition entity) {
        JobPositionVO vo = new JobPositionVO();
        BeanUtils.copyProperties(entity, vo);
        return vo;
    }
}
