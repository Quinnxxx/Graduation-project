package com.campus.recruit.common;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.io.Serializable;

/**
 * 统一响应结果封装
 *
 * <p>所有 Controller 接口统一返回该结构，包含状态码 code、提示信息 msg 与业务数据 data。</p>
 *
 * @param <T> 业务数据类型
 * @author campus-recruit
 * @since 1.0.0
 */
@Data
@Schema(description = "统一响应结果")
public class Result<T> implements Serializable {

    private static final long serialVersionUID = 1L;

    /** 状态码，见 {@link ResultCode} */
    @Schema(description = "状态码")
    private Integer code;

    /** 提示信息 */
    @Schema(description = "提示信息")
    private String msg;

    /** 业务数据 */
    @Schema(description = "响应数据")
    private T data;

    /**
     * 无参构造
     */
    public Result() {
    }

    /**
     * 全参构造
     *
     * @param code 状态码
     * @param msg  提示信息
     * @param data 业务数据
     */
    public Result(Integer code, String msg, T data) {
        this.code = code;
        this.msg = msg;
        this.data = data;
    }

    /**
     * 成功响应（无数据）
     *
     * @param <T> 数据类型
     * @return 成功结果
     */
    public static <T> Result<T> success() {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMsg(), null);
    }

    /**
     * 成功响应（带数据）
     *
     * @param data 业务数据
     * @param <T>  数据类型
     * @return 成功结果
     */
    public static <T> Result<T> success(T data) {
        return new Result<>(ResultCode.SUCCESS.getCode(), ResultCode.SUCCESS.getMsg(), data);
    }

    /**
     * 成功响应（带数据与自定义提示）
     *
     * @param data 业务数据
     * @param msg  自定义提示信息
     * @param <T>  数据类型
     * @return 成功结果
     */
    public static <T> Result<T> success(T data, String msg) {
        return new Result<>(ResultCode.SUCCESS.getCode(), msg, data);
    }

    /**
     * 失败响应（使用默认系统错误码 500）
     *
     * @param msg 错误提示信息
     * @param <T> 数据类型
     * @return 失败结果
     */
    public static <T> Result<T> fail(String msg) {
        return new Result<>(ResultCode.INTERNAL_ERROR.getCode(), msg, null);
    }

    /**
     * 失败响应（使用枚举状态码）
     *
     * @param resultCode 状态码枚举
     * @param <T>        数据类型
     * @return 失败结果
     */
    public static <T> Result<T> fail(ResultCode resultCode) {
        return new Result<>(resultCode.getCode(), resultCode.getMsg(), null);
    }

    /**
     * 失败响应（自定义状态码与提示）
     *
     * @param code 状态码
     * @param msg  错误提示信息
     * @param <T>  数据类型
     * @return 失败结果
     */
    public static <T> Result<T> fail(Integer code, String msg) {
        return new Result<>(code, msg, null);
    }

    /**
     * 判断响应是否成功
     *
     * @return 成功返回 true
     */
    public boolean isSuccess() {
        return this.code != null && this.code.equals(ResultCode.SUCCESS.getCode());
    }
}
