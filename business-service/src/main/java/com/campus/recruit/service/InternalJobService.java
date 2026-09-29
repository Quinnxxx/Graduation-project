package com.campus.recruit.service;

import com.campus.recruit.dto.InternalJobBatchDTO;
import com.campus.recruit.vo.InternalImportVO;

/**
 * 内部批量岗位入库服务
 *
 * <p>采集链路唯一写入口，仅允许携带正确内部令牌的调用方访问。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface InternalJobService {

    /**
     * 批量导入岗位记录（逐条按 job_hash 幂等）
     *
     * @param dto 批量岗位请求（1-200 条）
     * @return 入库结果（新建/跳过/失败计数）
     */
    InternalImportVO importBatch(InternalJobBatchDTO dto);
}