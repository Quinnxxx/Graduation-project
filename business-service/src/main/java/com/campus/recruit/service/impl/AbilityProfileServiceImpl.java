package com.campus.recruit.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.AbilitySaveDTO;
import com.campus.recruit.entity.AbilityProfile;
import com.campus.recruit.exception.BusinessException;
import com.campus.recruit.mapper.AbilityProfileMapper;
import com.campus.recruit.service.AbilityProfileService;
import com.campus.recruit.vo.AbilityTrendVO;
import com.campus.recruit.vo.AbilityVO;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 能力画像服务实现
 *
 * <p>getLatest 按维度分组取最新快照（LinkedHashMap 保序，快照日期倒序取首个）；
 * getTrend 返回指定维度的成长曲线数据点。</p>
 *
 * <p>写入语义为「每日一快照」：同用户 + 同维度 + 同快照日期当日重写覆盖
 * （先按条件逻辑删除旧记录再插入，事务保证原子性）。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
public class AbilityProfileServiceImpl extends ServiceImpl<AbilityProfileMapper, AbilityProfile> implements AbilityProfileService {

    /**
     * 写入能力画像快照（快照日期为空时默认当天）
     *
     * <p>「每日一快照」：写入前先删除同 userId + 同 dimension + 同 snapshotDate
     * 的旧记录（逻辑删除），使当日重写为覆盖语义；先删后插由事务保证原子性。</p>
     *
     * @param userId 用户 ID
     * @param dto    快照参数
     * @return 快照视图对象
     */
    @Override
    @Transactional(rollbackFor = Exception.class)
    public AbilityVO save(Long userId, AbilitySaveDTO dto) {
        AbilityProfile entity = new AbilityProfile();
        BeanUtil.copyProperties(dto, entity);
        entity.setUserId(userId);
        // 快照日期为空默认当天
        entity.setSnapshotDate(dto.getSnapshotDate() == null ? LocalDate.now() : dto.getSnapshotDate());
        // 每日一快照：先删同用户 + 同维度 + 同日期旧记录（逻辑删除），实现当日重写覆盖
        boolean overwritten = remove(new LambdaQueryWrapper<AbilityProfile>()
                .eq(AbilityProfile::getUserId, userId)
                .eq(AbilityProfile::getDimension, dto.getDimension())
                .eq(AbilityProfile::getSnapshotDate, entity.getSnapshotDate()));
        if (overwritten) {
            log.debug("当日快照已覆盖: userId={}, dimension={}, snapshotDate={}",
                    userId, dto.getDimension(), entity.getSnapshotDate());
        }
        save(entity);
        log.info("写入能力画像快照成功: userId={}, dimension={}, score={}, snapshotDate={}",
                userId, dto.getDimension(), dto.getDimensionScore(), entity.getSnapshotDate());
        return toVO(entity);
    }

    /**
     * 查询用户各维度最新能力画像
     *
     * <p>按快照日期倒序、id 倒序查询全部记录，用 LinkedHashMap 按维度分组只保留首个
     * （即每个维度最新的一条快照），保证返回顺序与查询顺序一致。</p>
     *
     * @param userId 用户 ID
     * @return 各维度最新快照列表
     */
    @Override
    public List<AbilityVO> getLatest(Long userId) {
        List<AbilityProfile> records = lambdaQuery()
                .eq(AbilityProfile::getUserId, userId)
                .orderByDesc(AbilityProfile::getSnapshotDate)
                .orderByDesc(AbilityProfile::getId)
                .list();
        // 按维度分组，只保留每组第一条（最新快照），LinkedHashMap 保持插入顺序
        Map<String, AbilityProfile> latestMap = new LinkedHashMap<>();
        for (AbilityProfile record : records) {
            latestMap.putIfAbsent(record.getDimension(), record);
        }
        return latestMap.values().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
    }

    /**
     * 查询指定维度的能力成长曲线（按快照日期正序，无数据返回空列表）
     *
     * @param userId    用户 ID
     * @param dimension 能力维度
     * @return 成长曲线数据点列表
     */
    @Override
    public List<AbilityTrendVO> getTrend(Long userId, String dimension) {
        // 二次校验：维度不能为空
        if (StringUtils.isBlank(dimension)) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "能力维度不能为空");
        }
        List<AbilityProfile> records = lambdaQuery()
                .eq(AbilityProfile::getUserId, userId)
                .eq(AbilityProfile::getDimension, dimension)
                .orderByAsc(AbilityProfile::getSnapshotDate)
                .orderByAsc(AbilityProfile::getId)
                .list();
        // 无数据返回空列表，不抛错
        if (records.isEmpty()) {
            return new ArrayList<>();
        }
        List<AbilityTrendVO> trend = records.stream()
                .map(this::toTrendVO)
                .collect(Collectors.toList());
        log.info("查询能力成长曲线成功: userId={}, dimension={}, pointCount={}", userId, dimension, trend.size());
        return trend;
    }

    /**
     * 实体转视图对象
     *
     * @param entity 能力画像实体
     * @return 能力画像视图对象
     */
    private AbilityVO toVO(AbilityProfile entity) {
        AbilityVO vo = new AbilityVO();
        BeanUtil.copyProperties(entity, vo);
        return vo;
    }

    /**
     * 实体转趋势数据点对象
     *
     * @param entity 能力画像实体
     * @return 能力成长曲线数据点对象
     */
    private AbilityTrendVO toTrendVO(AbilityProfile entity) {
        AbilityTrendVO vo = new AbilityTrendVO();
        BeanUtil.copyProperties(entity, vo);
        return vo;
    }
}
