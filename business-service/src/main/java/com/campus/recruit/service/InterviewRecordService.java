package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.dto.InterviewCreateDTO;
import com.campus.recruit.dto.InterviewMessageDTO;
import com.campus.recruit.dto.InterviewQueryDTO;
import com.campus.recruit.dto.InterviewUpdateDTO;
import com.campus.recruit.entity.InterviewRecord;
import com.campus.recruit.vo.InterviewMessageVO;
import com.campus.recruit.vo.InterviewVO;

/**
 * 模拟面试记录服务接口
 *
 * <p>所有按 id 操作的接口均校验记录归属当前用户，禁止操作他人数据。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface InterviewRecordService extends IService<InterviewRecord> {

    /**
     * 创建模拟面试（初始状态为进行中）
     *
     * @param userId 用户 ID
     * @param dto    创建参数
     * @return 面试视图对象（messages 为空）
     */
    InterviewVO create(Long userId, InterviewCreateDTO dto);

    /**
     * 分页查询当前用户的面试记录（列表不查消息）
     *
     * @param userId 用户 ID
     * @param dto    分页参数
     * @return 分页结果
     */
    PageResult<InterviewVO> pageQuery(Long userId, InterviewQueryDTO dto);

    /**
     * 查询面试详情（含全部对话消息，按创建时间正序）
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     * @return 面试视图对象
     */
    InterviewVO getDetail(Long userId, Long id);

    /**
     * 更新面试记录（结束回填，仅更新非 null 字段，校验归属）
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     * @param dto    更新参数
     * @return 更新后的面试视图对象（不含消息）
     */
    InterviewVO update(Long userId, Long id, InterviewUpdateDTO dto);

    /**
     * 追加面试消息（校验归属与面试进行中状态，question 消息同步自增提问数）
     *
     * @param userId            用户 ID
     * @param interviewRecordId 面试记录 ID
     * @param dto               消息参数
     * @return 消息视图对象
     */
    InterviewMessageVO addMessage(Long userId, Long interviewRecordId, InterviewMessageDTO dto);

    /**
     * 删除面试记录（逻辑删除记录，并物理删除其全部消息，校验归属）
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     */
    void delete(Long userId, Long id);
}
