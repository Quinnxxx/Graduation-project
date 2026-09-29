package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.dto.AbilitySaveDTO;
import com.campus.recruit.entity.AbilityProfile;
import com.campus.recruit.vo.AbilityTrendVO;
import com.campus.recruit.vo.AbilityVO;

import java.util.List;

/**
 * 能力画像服务接口
 *
 * <p>数据由面试复盘 Agent 在每次面试结束后写入各维度快照，本服务提供查询与写入能力。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface AbilityProfileService extends IService<AbilityProfile> {

    /**
     * 写入能力画像快照
     *
     * @param userId 用户 ID
     * @param dto    快照参数
     * @return 快照视图对象
     */
    AbilityVO save(Long userId, AbilitySaveDTO dto);

    /**
     * 查询用户各维度最新能力画像
     *
     * @param userId 用户 ID
     * @return 各维度最新快照列表
     */
    List<AbilityVO> getLatest(Long userId);

    /**
     * 查询指定维度的能力成长曲线（按快照日期正序）
     *
     * @param userId    用户 ID
     * @param dimension 能力维度
     * @return 成长曲线数据点列表，无数据返回空列表
     */
    List<AbilityTrendVO> getTrend(Long userId, String dimension);
}
