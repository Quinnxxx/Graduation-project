package com.campus.recruit.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.bean.copier.CopyOptions;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.InterviewCreateDTO;
import com.campus.recruit.dto.InterviewMessageDTO;
import com.campus.recruit.dto.InterviewQueryDTO;
import com.campus.recruit.dto.InterviewUpdateDTO;
import com.campus.recruit.entity.InterviewMessage;
import com.campus.recruit.entity.InterviewRecord;
import com.campus.recruit.exception.BusinessException;
import com.campus.recruit.mapper.InterviewMessageMapper;
import com.campus.recruit.mapper.InterviewRecordMapper;
import com.campus.recruit.service.InterviewRecordService;
import com.campus.recruit.vo.InterviewMessageVO;
import com.campus.recruit.vo.InterviewVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

/**
 * 模拟面试记录服务实现
 *
 * <p>安全约定：按 id 操作（详情/更新/追加消息/删除）必须先查记录再校验归属，
 * 归属不匹配抛出 {@link ResultCode#FORBIDDEN}，禁止操作他人数据。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class InterviewRecordServiceImpl extends ServiceImpl<InterviewRecordMapper, InterviewRecord> implements InterviewRecordService {

    /** 默认难度：2 中等 */
    private static final Integer DEFAULT_DIFFICULTY = 2;

    /** 面试进行中状态 */
    private static final Integer STATUS_IN_PROGRESS = 1;

    /** 消息类型：问题 */
    private static final String MESSAGE_TYPE_QUESTION = "question";

    private final InterviewMessageMapper interviewMessageMapper;

    /**
     * 创建模拟面试（初始状态进行中，提问数与时长初始为 0）
     *
     * @param userId 用户 ID
     * @param dto    创建参数
     * @return 面试视图对象（messages 为空）
     */
    @Override
    public InterviewVO create(Long userId, InterviewCreateDTO dto) {
        InterviewRecord entity = new InterviewRecord();
        BeanUtil.copyProperties(dto, entity);
        entity.setUserId(userId);
        // 难度为空时使用默认值 2 中等
        entity.setDifficultyLevel(dto.getDifficultyLevel() == null ? DEFAULT_DIFFICULTY : dto.getDifficultyLevel());
        // 初始值：进行中、提问数 0、时长 0
        entity.setStatus(STATUS_IN_PROGRESS);
        entity.setQuestionCount(0);
        entity.setDurationSeconds(0);
        save(entity);
        log.info("创建模拟面试成功: userId={}, interviewId={}, interviewType={}",
                userId, entity.getId(), dto.getInterviewType());
        return toVO(entity);
    }

    /**
     * 分页查询当前用户的面试记录（列表不查消息，按创建时间倒序）
     *
     * @param userId 用户 ID
     * @param dto    分页参数
     * @return 分页结果
     */
    @Override
    public PageResult<InterviewVO> pageQuery(Long userId, InterviewQueryDTO dto) {
        Page<InterviewRecord> page = lambdaQuery()
                .eq(InterviewRecord::getUserId, userId)
                .eq(dto.getInterviewType() != null, InterviewRecord::getInterviewType, dto.getInterviewType())
                .orderByDesc(InterviewRecord::getCreateTime)
                .page(new Page<>(dto.getPageNum(), dto.getPageSize()));
        List<InterviewVO> records = page.getRecords().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
        return PageResult.of(records, page.getTotal(), (long) dto.getPageNum(), (long) dto.getPageSize());
    }

    /**
     * 查询面试详情（先查记录校验归属，再查全部消息按创建时间正序组装）
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     * @return 面试视图对象
     */
    @Override
    public InterviewVO getDetail(Long userId, Long id) {
        InterviewRecord entity = getOwnedRecord(userId, id);
        InterviewVO vo = toVO(entity);
        // 组装该面试的全部对话消息（按创建时间正序，保证对话顺序）
        List<InterviewMessageVO> messages = interviewMessageMapper.selectList(
                        new LambdaQueryWrapper<InterviewMessage>()
                                .eq(InterviewMessage::getInterviewRecordId, id)
                                .orderByAsc(InterviewMessage::getCreateTime))
                .stream()
                .map(this::toMessageVO)
                .collect(Collectors.toList());
        vo.setMessages(messages);
        return vo;
    }

    /**
     * 更新面试记录（结束回填，仅更新非 null 字段，先查记录再校验归属）
     *
     * <p>字段级更新约定：null 表示不修改该字段；空字符串表示清空。</p>
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     * @param dto    更新参数
     * @return 更新后的面试视图对象（不含消息）
     */
    @Override
    public InterviewVO update(Long userId, Long id, InterviewUpdateDTO dto) {
        InterviewRecord entity = getOwnedRecord(userId, id);
        // 忽略 null 字段，避免局部更新时清空其他字段
        BeanUtil.copyProperties(dto, entity, CopyOptions.create().setIgnoreNullValue(true));
        updateById(entity);
        log.info("更新模拟面试成功: userId={}, interviewId={}", userId, id);
        return toVO(entity);
    }

    /**
     * 追加面试消息（校验归属与面试进行中状态；question 消息同步自增提问数）
     *
     * @param userId            用户 ID
     * @param interviewRecordId 面试记录 ID
     * @param dto               消息参数
     * @return 消息视图对象
     */
    @Override
    public InterviewMessageVO addMessage(Long userId, Long interviewRecordId, InterviewMessageDTO dto) {
        InterviewRecord entity = getOwnedRecord(userId, interviewRecordId);
        // 已结束的面试不能再追加消息
        if (!STATUS_IN_PROGRESS.equals(entity.getStatus())) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "面试已结束，不能追加消息");
        }
        // 组装并插入消息
        InterviewMessage message = new InterviewMessage();
        message.setInterviewRecordId(interviewRecordId);
        message.setRole(dto.getRole());
        message.setMessageType(dto.getMessageType());
        message.setContent(dto.getContent());
        message.setScore(dto.getScore());
        interviewMessageMapper.insert(message);
        // question 消息：提问数量自增 1
        if (MESSAGE_TYPE_QUESTION.equals(dto.getMessageType())) {
            entity.setQuestionCount(entity.getQuestionCount() + 1);
            updateById(entity);
        }
        log.info("追加面试消息成功: userId={}, interviewId={}, messageId={}, messageType={}",
                userId, interviewRecordId, message.getId(), dto.getMessageType());
        return toMessageVO(message);
    }

    /**
     * 删除面试记录（逻辑删除记录，并物理删除其全部消息，先查记录再校验归属）
     *
     * <p>interview_message 无逻辑删除字段，删除消息采用物理删除。</p>
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     */
    @Override
    public void delete(Long userId, Long id) {
        InterviewRecord entity = getOwnedRecord(userId, id);
        // 先物理删除该面试的全部消息
        List<Long> messageIds = interviewMessageMapper.selectList(
                        new LambdaQueryWrapper<InterviewMessage>()
                                .eq(InterviewMessage::getInterviewRecordId, id))
                .stream()
                .map(InterviewMessage::getId)
                .collect(Collectors.toList());
        if (!messageIds.isEmpty()) {
            interviewMessageMapper.deleteBatchIds(messageIds);
        }
        // 再逻辑删除面试记录
        removeById(entity.getId());
        log.info("删除模拟面试成功: userId={}, interviewId={}, messageCount={}", userId, id, messageIds.size());
    }

    /**
     * 按 id 查询记录并校验归属当前用户
     *
     * @param userId 用户 ID
     * @param id     面试记录 ID
     * @return 面试记录实体
     */
    private InterviewRecord getOwnedRecord(Long userId, Long id) {
        InterviewRecord entity = getById(id);
        if (entity == null) {
            throw new BusinessException(ResultCode.INTERVIEW_RECORD_NOT_EXIST);
        }
        // 安全红线：校验记录归属，禁止操作他人数据
        if (!entity.getUserId().equals(userId)) {
            throw new BusinessException(ResultCode.FORBIDDEN, "无权操作他人数据");
        }
        return entity;
    }

    /**
     * 实体转视图对象（不含消息列表）
     *
     * @param entity 面试记录实体
     * @return 面试视图对象
     */
    private InterviewVO toVO(InterviewRecord entity) {
        InterviewVO vo = new InterviewVO();
        BeanUtil.copyProperties(entity, vo);
        return vo;
    }

    /**
     * 消息实体转视图对象
     *
     * @param message 面试消息实体
     * @return 面试消息视图对象
     */
    private InterviewMessageVO toMessageVO(InterviewMessage message) {
        InterviewMessageVO vo = new InterviewMessageVO();
        BeanUtil.copyProperties(message, vo);
        return vo;
    }
}
