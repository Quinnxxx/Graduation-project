package com.campus.recruit.exception;

import com.campus.recruit.common.Result;
import com.campus.recruit.common.ResultCode;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * 全局异常处理器
 *
 * <p>统一捕获参数校验异常、业务异常与系统异常，转换为 {@link Result} 结构返回，避免异常堆栈直接暴露给前端。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * 处理业务异常
     *
     * @param e 业务异常
     * @return 统一响应结果
     */
    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusinessException(BusinessException e) {
        log.warn("[业务异常] code={}, msg={}", e.getCode(), e.getMessage());
        return Result.fail(e.getCode(), e.getMessage());
    }

    /**
     * 处理 @RequestBody 参数校验异常
     *
     * @param e 参数校验异常
     * @return 统一响应结果
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleMethodArgumentNotValidException(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .findFirst()
                .orElse(ResultCode.BAD_REQUEST.getMsg());
        log.warn("[参数校验失败] {}", message);
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), message);
    }

    /**
     * 处理表单/Query 参数绑定异常
     *
     * @param e 绑定异常
     * @return 统一响应结果
     */
    @ExceptionHandler(BindException.class)
    public Result<Void> handleBindException(BindException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .findFirst()
                .orElse(ResultCode.BAD_REQUEST.getMsg());
        log.warn("[参数绑定失败] {}", message);
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), message);
    }

    /**
     * 处理方法级参数校验异常（@Validated 作用于方法参数）
     *
     * @param e 约束校验异常
     * @return 统一响应结果
     */
    @ExceptionHandler(ConstraintViolationException.class)
    public Result<Void> handleConstraintViolationException(ConstraintViolationException e) {
        String message = e.getConstraintViolations().stream()
                .map(ConstraintViolation -> ConstraintViolation.getMessage())
                .findFirst()
                .orElse(ResultCode.BAD_REQUEST.getMsg());
        log.warn("[约束校验失败] {}", message);
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), message);
    }

    /**
     * 处理缺少必要请求参数异常
     *
     * @param e 缺参异常
     * @return 统一响应结果
     */
    @ExceptionHandler(MissingServletRequestParameterException.class)
    public Result<Void> handleMissingServletRequestParameterException(MissingServletRequestParameterException e) {
        String message = "缺少必要参数: " + e.getParameterName();
        log.warn("[缺少参数] {}", message);
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), message);
    }

    /**
     * 处理参数类型转换异常
     *
     * @param e 类型转换异常
     * @return 统一响应结果
     */
    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public Result<Void> handleMethodArgumentTypeMismatchException(MethodArgumentTypeMismatchException e) {
        String message = "参数类型错误: " + e.getName();
        log.warn("[参数类型错误] {}", message);
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), message);
    }

    /**
     * 处理请求体不可读异常（JSON 格式错误或为空）
     *
     * @param e 请求体异常
     * @return 统一响应结果
     */
    @ExceptionHandler(HttpMessageNotReadableException.class)
    public Result<Void> handleHttpMessageNotReadableException(HttpMessageNotReadableException e) {
        log.warn("[请求体错误] {}", e.getMessage());
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), "请求体格式错误或为空");
    }

    /**
     * 处理资源不存在异常（404）
     *
     * @param e 资源不存在异常
     * @return 统一响应结果
     */
    @ExceptionHandler(NoResourceFoundException.class)
    public Result<Void> handleNoResourceFoundException(NoResourceFoundException e) {
        log.warn("[资源不存在] {}", e.getResourcePath());
        return Result.fail(ResultCode.NOT_FOUND);
    }

    /**
     * 处理上传文件超过 Multipart 限制异常（业务层 5MB 校验的兜底）
     *
     * @param e 上传大小异常
     * @return 统一响应结果
     */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public Result<Void> handleMaxUploadSizeExceededException(MaxUploadSizeExceededException e) {
        log.warn("[上传超限] {}", e.getMessage());
        return Result.fail(ResultCode.BAD_REQUEST.getCode(), "上传文件不能超过 5MB");
    }

    /**
     * 处理未知系统异常（兜底）
     *
     * @param e 系统异常
     * @return 统一响应结果
     */
    @ExceptionHandler(Exception.class)
    public Result<Void> handleException(Exception e) {
        log.error("[系统异常]", e);
        return Result.fail(ResultCode.INTERNAL_ERROR);
    }
}
