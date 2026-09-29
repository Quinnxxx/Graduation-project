package com.campus.recruit.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.bean.copier.CopyOptions;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.SessionCreateDTO;
import com.campus.recruit.dto.SessionQueryDTO;
import com.campus.recruit.dto.SessionUpdateDTO;
import com.campus.recruit.entity.SessionRecord;
import com.campus.recruit.exception.BusinessException;
import com.campus.recruit.mapper.SessionRecordMapper;
import com.campus.recruit.service.SessionRecordService;
import com.campus.recruit.vo.SessionVO;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 用户会话服务实现
 *
 * <p>安全约定：按 id 操作（更新/删除）必须先查记录再校验归属，
 * 归属不匹配抛出 {@link ResultCode#FORBIDDEN}，禁止操作他人数据。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
public class SessionRecordServiceImpl extends ServiceImpl<SessionRecordMapper, SessionRecord> implements SessionRecordService {

    /** 默认会话标题 */
    private static final String DEFAULT_TITLE = "新建会话";

    /**
     * 创建用户会话（初始状态为进行中，标题为空时使用默认值）
     *
     * @param userId 用户 ID
     * @param dto    创建参数
     * @return 会话视图对象
     */
    @Override
    public SessionVO create(Long userId, SessionCreateDTO dto) {
        SessionRecord entity = new SessionRecord();
        BeanUtil.copyProperties(dto, entity);
        entity.setUserId(userId);
        // 标题为空使用默认值
        entity.setTitle(StringUtils.isBlank(dto.getTitle()) ? DEFAULT_TITLE : dto.getTitle());
        // 初始状态：1 进行中，会话结束后由 update 置为 2
        entity.setStatus(1);
        save(entity);
        log.info("创建用户会话成功: userId={}, sessionId={}, sessionType={}", userId, entity.getId(), dto.getSessionType());
        return toVO(entity);
    }

    /**
     * 分页查询当前用户的会话记录（按创建时间倒序）
     *
     * @param userId 用户 ID
     * @param dto    分页参数
     * @return 分页结果
     */
    @Override
    public PageResult<SessionVO> pageQuery(Long userId, SessionQueryDTO dto) {
        Page<SessionRecord> page = lambdaQuery()
                .eq(SessionRecord::getUserId, userId)
                .eq(dto.getSessionType() != null, SessionRecord::getSessionType, dto.getSessionType())
                .orderByDesc(SessionRecord::getCreateTime)
                .page(new Page<>(dto.getPageNum(), dto.getPageSize()));
        List<SessionVO> records = page.getRecords().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
        return PageResult.of(records, page.getTotal(), (long) dto.getPageNum(), (long) dto.getPageSize());
    }

    /**
     * 更新用户会话（仅更新非 null 字段，先查记录再校验归属）
     *
     * <p>字段级更新约定：null 表示不修改该字段；空字符串表示清空。</p>
     *
     * @param userId 用户 ID
     * @param id     会话 ID
     * @param dto    更新参数
     * @return 更新后的会话视图对象
     */
    @Override
    public SessionVO update(Long userId, Long id, SessionUpdateDTO dto) {
        SessionRecord entity = getOwnedRecord(userId, id);
        // 忽略 null 字段，避免局部更新时清空其他字段
        BeanUtil.copyProperties(dto, entity, CopyOptions.create().setIgnoreNullValue(true));
        updateById(entity);
        log.info("更新用户会话成功: userId={}, sessionId={}", userId, id);
        return toVO(entity);
    }

    /**
     * 删除用户会话（逻辑删除，先查记录再校验归属）
     *
     * @param userId 用户 ID
     * @param id     会话 ID
     */
    @Override
    public void delete(Long userId, Long id) {
        SessionRecord entity = getOwnedRecord(userId, id);
        removeById(entity.getId());
        log.info("删除用户会话成功: userId={}, sessionId={}", userId, id);
    }

    /**
     * 按 id 查询记录并校验归属当前用户
     *
     * @param userId 用户 ID
     * @param id     会话 ID
     * @return 会话记录实体
     */
    private SessionRecord getOwnedRecord(Long userId, Long id) {
        SessionRecord entity = getById(id);
        if (entity == null) {
            throw new BusinessException(ResultCode.SESSION_RECORD_NOT_EXIST);
        }
        // 安全红线：校验记录归属，禁止操作他人数据
        if (!entity.getUserId().equals(userId)) {
            throw new BusinessException(ResultCode.FORBIDDEN, "无权操作他人数据");
        }
        return entity;
    }

    /**
     * 实体转视图对象
     *
     * @param entity 会话记录实体
     * @return 会话视图对象
     */
    private SessionVO toVO(SessionRecord entity) {
        SessionVO vo = new SessionVO();
        BeanUtil.copyProperties(entity, vo);
        return vo;
    }
}
