package com.campus.recruit.common;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;
import java.util.Collections;
import java.util.List;

/**
 * 分页结果封装
 *
 * @param <T> 列表元素类型
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "分页结果")
public class PageResult<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 总记录数 */
    @Schema(description = "总记录数")
    private Long total;

    /** 当前页码 */
    @Schema(description = "当前页码")
    private Long pageNum;

    /** 每页条数 */
    @Schema(description = "每页条数")
    private Long pageSize;

    /** 当前页数据 */
    @Schema(description = "当前页数据列表")
    private List<T> list;

    /**
     * 无参构造
     */
    public PageResult() {
    }

    /**
     * 构造分页结果
     *
     * @param list     当前页数据
     * @param total    总记录数
     * @param pageNum  当前页码
     * @param pageSize 每页条数
     * @param <T>      元素类型
     * @return 分页结果
     */
    public static <T> PageResult<T> of(List<T> list, Long total, Long pageNum, Long pageSize) {
        PageResult<T> pageResult = new PageResult<>();
        pageResult.setList(list);
        pageResult.setTotal(total);
        pageResult.setPageNum(pageNum);
        pageResult.setPageSize(pageSize);
        return pageResult;
    }

    /**
     * 返回空分页结果
     *
     * @param <T> 元素类型
     * @return 空分页结果
     */
    public static <T> PageResult<T> empty() {
        return of(Collections.emptyList(), 0L, 1L, 10L);
    }
}
