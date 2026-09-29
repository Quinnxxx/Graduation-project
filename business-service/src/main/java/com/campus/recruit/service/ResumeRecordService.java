package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.dto.ResumeQueryDTO;
import com.campus.recruit.dto.ResumeSaveDTO;
import com.campus.recruit.dto.ResumeUpdateDTO;
import com.campus.recruit.entity.ResumeRecord;
import com.campus.recruit.vo.ResumeUploadVO;
import com.campus.recruit.vo.ResumeVO;
import org.springframework.web.multipart.MultipartFile;

/**
 * 简历记录服务接口
 *
 * <p>所有按 id 操作的接口均校验记录归属当前用户，禁止操作他人数据。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface ResumeRecordService extends IService<ResumeRecord> {

    /**
     * 创建简历记录（初始状态为处理中）
     *
     * @param userId 用户 ID
     * @param dto    创建参数
     * @return 简历记录视图对象
     */
    ResumeVO create(Long userId, ResumeSaveDTO dto);

    /**
     * 分页查询当前用户的简历记录
     *
     * @param userId 用户 ID
     * @param dto    分页参数
     * @return 分页结果
     */
    PageResult<ResumeVO> pageQuery(Long userId, ResumeQueryDTO dto);

    /**
     * 查询简历记录详情（校验归属）
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     * @return 简历记录视图对象
     */
    ResumeVO getDetail(Long userId, Long id);

    /**
     * 更新简历记录（AI 优化回填，仅更新非 null 字段，校验归属）
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     * @param dto    更新参数
     * @return 更新后的简历记录视图对象
     */
    ResumeVO update(Long userId, Long id, ResumeUpdateDTO dto);

    /**
     * 删除简历记录（逻辑删除，校验归属）
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     */
    void delete(Long userId, Long id);

    /**
     * 上传 PDF 简历：校验、落盘并提取文本（不落库，由前端随创建请求回传文件字段）
     *
     * @param userId 用户 ID
     * @param file   PDF 文件（≤5MB，application/pdf）
     * @return 上传结果（fileName / fileSize / filePath / text）
     */
    ResumeUploadVO uploadPdf(Long userId, MultipartFile file);
}
