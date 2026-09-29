package com.campus.recruit.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.bean.copier.CopyOptions;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.dto.UserProfileSaveDTO;
import com.campus.recruit.entity.UserProfile;
import com.campus.recruit.mapper.UserProfileMapper;
import com.campus.recruit.service.UserProfileService;
import com.campus.recruit.vo.UserProfileVO;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * 用户求职画像服务实现
 *
 * <p>skillTags 入库时转为 JSON 字符串（{@link JSONUtil#toJsonStr(Object)}），
 * 返回时转回 {@link List}（{@link JSONUtil#toList(String, Class)}）。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
public class UserProfileServiceImpl extends ServiceImpl<UserProfileMapper, UserProfile> implements UserProfileService {

    /**
     * 根据用户 ID 查询求职画像
     *
     * @param userId 用户 ID
     * @return 用户画像视图对象，不存在时返回 null
     */
    @Override
    public UserProfileVO getByUserId(Long userId) {
        UserProfile entity = lambdaQuery()
                .eq(UserProfile::getUserId, userId)
                .one();
        return entity == null ? null : toVO(entity);
    }

    /**
     * 创建或更新当前用户求职画像（先查后插，保证 user_id 唯一幂等）
     *
     * <p>字段级更新约定：null 表示不修改该字段；空字符串表示清空；
     * skillTags 传空数组 [] 表示清空技能标签。</p>
     *
     * @param userId 用户 ID
     * @param dto    画像保存参数
     * @return 保存后的用户画像视图对象
     */
    @Override
    public UserProfileVO saveOrUpdate(Long userId, UserProfileSaveDTO dto) {
        UserProfile entity = lambdaQuery()
                .eq(UserProfile::getUserId, userId)
                .one();
        if (entity == null) {
            // 不存在则新增（全量拷贝，空值按默认语义入库）
            entity = new UserProfile();
            BeanUtil.copyProperties(dto, entity);
            entity.setUserId(userId);
            entity.setSkillTags(toJsonStr(dto.getSkillTags()));
            entity.setStatus(1);
            save(entity);
            log.info("创建用户画像成功: userId={}", userId);
        } else {
            // 存在则更新：忽略 null 字段，避免局部更新时清空其他字段
            BeanUtil.copyProperties(dto, entity, CopyOptions.create().setIgnoreNullValue(true));
            // skillTags 单独处理：仅当显式传值（含空数组）时才更新，null 表示不修改
            if (dto.getSkillTags() != null) {
                entity.setSkillTags(toJsonStr(dto.getSkillTags()));
            }
            updateById(entity);
            log.info("更新用户画像成功: userId={}", userId);
        }
        return toVO(entity);
    }

    /**
     * 技能标签列表转 JSON 字符串（空列表存 []，避免存储 null 字符串）
     *
     * @param skillTags 技能标签列表，可为 null
     * @return JSON 字符串
     */
    private String toJsonStr(List<String> skillTags) {
        return skillTags == null ? "[]" : JSONUtil.toJsonStr(skillTags);
    }

    /**
     * 实体转视图对象（skillTags 由 JSON 字符串转回 List）
     *
     * @param entity 用户画像实体
     * @return 用户画像视图对象
     */
    private UserProfileVO toVO(UserProfile entity) {
        UserProfileVO vo = new UserProfileVO();
        BeanUtil.copyProperties(entity, vo);
        vo.setSkillTags(StringUtils.isNotBlank(entity.getSkillTags())
                ? JSONUtil.toList(entity.getSkillTags(), String.class)
                : new ArrayList<>());
        return vo;
    }
}
