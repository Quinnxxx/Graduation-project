package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.dto.SessionCreateDTO;
import com.campus.recruit.dto.SessionQueryDTO;
import com.campus.recruit.dto.SessionUpdateDTO;
import com.campus.recruit.entity.SessionRecord;
import com.campus.recruit.vo.SessionVO;

/**
 * 用户会话服务接口
 *
 * <p>所有按 id 操作的接口均校验记录归属当前用户，禁止操作他人数据。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface SessionRecordService extends IService<SessionRecord> {

    /**
     * 创建用户会话（初始状态为进行中）
     *
     * @param userId 用户 ID
     * @param dto    创建参数
     * @return 会话视图对象
     */
    SessionVO create(Long userId, SessionCreateDTO dto);

    /**
     * 分页查询当前用户的会话记录
     *
     * @param userId 用户 ID
     * @param dto    分页参数
     * @return 分页结果
     */
    PageResult<SessionVO> pageQuery(Long userId, SessionQueryDTO dto);

    /**
     * 更新用户会话（仅更新非 null 字段，校验归属）
     *
     * @param userId 用户 ID
     * @param id     会话 ID
     * @param dto    更新参数
     * @return 更新后的会话视图对象
     */
    SessionVO update(Long userId, Long id, SessionUpdateDTO dto);

    /**
     * 删除用户会话（逻辑删除，校验归属）
     *
     * @param userId 用户 ID
     * @param id     会话 ID
     */
    void delete(Long userId, Long id);
}
