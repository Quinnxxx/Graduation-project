package com.campus.recruit.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.campus.recruit.dto.UserProfileSaveDTO;
import com.campus.recruit.entity.UserProfile;
import com.campus.recruit.vo.UserProfileVO;

/**
 * 用户求职画像服务接口
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public interface UserProfileService extends IService<UserProfile> {

    /**
     * 根据用户 ID 查询求职画像
     *
     * @param userId 用户 ID
     * @return 用户画像视图对象，不存在时返回 null（由前端引导填写）
     */
    UserProfileVO getByUserId(Long userId);

    /**
     * 创建或更新当前用户求职画像（先查后插，保证 user_id 唯一幂等）
     *
     * @param userId 用户 ID
     * @param dto    画像保存参数
     * @return 保存后的用户画像视图对象
     */
    UserProfileVO saveOrUpdate(Long userId, UserProfileSaveDTO dto);
}
