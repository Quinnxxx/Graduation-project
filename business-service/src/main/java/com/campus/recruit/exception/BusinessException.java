package com.campus.recruit.exception;

import com.campus.recruit.common.ResultCode;
import lombok.Getter;

/**
 * 自定义业务异常
 *
 * <p>业务代码中遇到可预期的异常时统一抛出本异常，由 {@link GlobalExceptionHandler} 统一捕获并返回。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Getter
public class BusinessException extends RuntimeException {

    private static final long serialVersionUID = 1L;

    /** 业务状态码 */
    private final Integer code;

    /**
     * 使用默认系统错误码（500）构造异常
     *
     * @param message 异常信息
     */
    public BusinessException(String message) {
        super(message);
        this.code = ResultCode.INTERNAL_ERROR.getCode();
    }

    /**
     * 使用枚举状态码构造异常
     *
     * @param resultCode 状态码枚举
     */
    public BusinessException(ResultCode resultCode) {
        super(resultCode.getMsg());
        this.code = resultCode.getCode();
    }

    /**
     * 使用枚举状态码与自定义信息构造异常
     *
     * @param resultCode 状态码枚举
     * @param message    自定义异常信息
     */
    public BusinessException(ResultCode resultCode, String message) {
        super(message);
        this.code = resultCode.getCode();
    }

    /**
     * 使用自定义状态码与信息构造异常
     *
     * @param code    状态码
     * @param message 异常信息
     */
    public BusinessException(Integer code, String message) {
        super(message);
        this.code = code;
    }
}
