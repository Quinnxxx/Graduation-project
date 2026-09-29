package com.campus.recruit.entity;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableLogic;
import lombok.Data;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 * 基础实体类
 *
 * <p>所有业务实体继承本类，统一包含主键、创建时间、更新时间与逻辑删除标记。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
public abstract class BaseEntity implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 主键（雪花算法生成） */
    @TableId(value = "id", type = IdType.ASSIGN_ID)
    private Long id;

    /** 创建时间（插入时自动填充） */
    @TableField(value = "create_time", fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    /** 更新时间（插入与更新时自动填充） */
    @TableField(value = "update_time", fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    /** 逻辑删除标记（0 未删除，1 已删除，查询自动过滤） */
    @TableLogic
    @TableField(value = "is_deleted", fill = FieldFill.INSERT)
    private Integer isDeleted;
}
