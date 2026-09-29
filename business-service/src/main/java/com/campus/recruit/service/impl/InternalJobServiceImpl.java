package com.campus.recruit.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.campus.recruit.dto.InternalJobBatchDTO;
import com.campus.recruit.dto.InternalJobItemDTO;
import com.campus.recruit.entity.JobPosition;
import com.campus.recruit.service.InternalJobService;
import com.campus.recruit.service.JobPositionService;
import com.campus.recruit.vo.InternalImportVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.util.DigestUtils;

import java.nio.charset.StandardCharsets;

/**
 * 内部批量岗位入库服务实现
 *
 * <p>逐条处理语义：先按 {@code job_hash} 查询存在即跳过，不存在则插入；
 * 插入阶段再兜底唯一键冲突（并发 / 逻辑删记录仍占唯一键场景）按跳过处理，
 * 其它异常按失败计数并记录明细日志。全程不整批回滚——单条失败不影响其余
 * 记录，保证同批 / 跨批重复 hash 永不重复进表。</p>
 *
 * <p>{@code job_hash} 键规则：MD5(公司|岗位|城市|链接)，与实体字段注释一致，
 * 任一属性为空时以空串参与拼接，保证同岗位不同城市 / 链接可区分。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InternalJobServiceImpl implements InternalJobService {

    private final JobPositionService jobPositionService;

    /**
     * 批量导入岗位记录（逐条按 job_hash 幂等）
     *
     * @param dto 批量岗位请求
     * @return 入库结果（新建/跳过/失败计数，失败明细记录日志）
     */
    @Override
    public InternalImportVO importBatch(InternalJobBatchDTO dto) {
        InternalImportVO result = new InternalImportVO();
        for (InternalJobItemDTO item : dto.getItems()) {
            String jobHash = computeJobHash(item);
            // 一、预判去重：job_hash 已存在（含逻辑删除记录，@TableLogic 查询自动过滤）
            long exists = jobPositionService.count(
                    new LambdaQueryWrapper<JobPosition>().eq(JobPosition::getJobHash, jobHash));
            if (exists > 0) {
                result.setSkipped(result.getSkipped() + 1);
                log.info("[内部入库] 岗位已存在跳过: company={}, title={}",
                        item.getCompanyName(), item.getJobTitle());
                continue;
            }
            // 二、插入（唯一键冲突兜底跳过；幂等键保证永不重复进表）
            try {
                jobPositionService.save(toEntity(item, jobHash));
                result.setCreated(result.getCreated() + 1);
            } catch (DuplicateKeyException e) {
                result.setSkipped(result.getSkipped() + 1);
                log.info("[内部入库] 岗位唯一键冲突跳过: company={}, title={}",
                        item.getCompanyName(), item.getJobTitle());
            } catch (Exception e) {
                result.setFailed(result.getFailed() + 1);
                log.warn("[内部入库] 岗位写入失败: company={}, title={}, hash={}",
                        item.getCompanyName(), item.getJobTitle(), jobHash, e);
            }
        }
        log.info("[内部入库] 批量导入完成: created={}, skipped={}, failed={}",
                result.getCreated(), result.getSkipped(), result.getFailed());
        return result;
    }

    /**
     * 计算岗位去重指纹：MD5(公司|岗位|城市|链接)，空值以空串参与拼接。
     *
     * @param item 岗位条目
     * @return 32 位小写 MD5 指纹
     */
    private String computeJobHash(InternalJobItemDTO item) {
        String raw = String.join("|",
                StringUtils.defaultString(item.getCompanyName()),
                StringUtils.defaultString(item.getJobTitle()),
                StringUtils.defaultString(item.getCity()),
                StringUtils.defaultString(item.getLink()));
        return DigestUtils.md5DigestAsHex(raw.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * 岗位条目映射为实体（extCompany 当前表无对应列，不落库）。
     *
     * @param item    岗位条目
     * @param jobHash 去重指纹
     * @return 待写入实体（状态默认在招）
     */
    private JobPosition toEntity(InternalJobItemDTO item, String jobHash) {
        JobPosition entity = new JobPosition();
        entity.setCompanyName(item.getCompanyName());
        entity.setPositionName(item.getJobTitle());
        entity.setWorkCity(item.getCity());
        entity.setJobCategory(item.getJobCategory());
        entity.setSalaryNote(item.getSalaryRange());
        entity.setJobDescription(item.getJobDetails());
        entity.setPublishTime(item.getPublishDate());
        entity.setSourceUrl(item.getLink());
        entity.setSourceChannel(item.getSourceChannel());
        entity.setJobHash(jobHash);
        entity.setStatus(1);
        return entity;
    }
}