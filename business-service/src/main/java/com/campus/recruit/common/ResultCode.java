package com.campus.recruit.common;

import lombok.Getter;

/**
 * 统一状态码枚举
 *
 * <p>200-499 为 HTTP 语义状态码；1000+ 为业务状态码，按业务模块递增扩展。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Getter
public enum ResultCode {

    /** 操作成功 */
    SUCCESS(200, "操作成功"),

    /** 请求参数错误 */
    BAD_REQUEST(400, "请求参数错误"),

    /** 未登录或登录已过期 */
    UNAUTHORIZED(401, "未登录或登录已过期"),

    /** 没有操作权限 */
    FORBIDDEN(403, "没有操作权限"),

    /** 请求资源不存在 */
    NOT_FOUND(404, "请求资源不存在"),

    /** 系统内部错误 */
    INTERNAL_ERROR(500, "系统内部错误"),

    /* ==================== 业务状态码（1000+） ==================== */

    /** 用户不存在 */
    USER_NOT_EXIST(1001, "用户不存在"),

    /** 用户名已存在 */
    USERNAME_EXISTS(1002, "用户名已存在"),

    /** 用户名或密码错误 */
    USERNAME_OR_PASSWORD_ERROR(1003, "用户名或密码错误"),

    /** 账号已被禁用 */
    USER_DISABLED(1004, "账号已被禁用"),

    /** 两次输入的密码不一致 */
    PASSWORD_NOT_MATCH(1005, "两次输入的密码不一致"),

    /** 无效的令牌 */
    TOKEN_INVALID(1006, "无效的令牌"),

    /** 令牌已过期 */
    TOKEN_EXPIRED(1007, "令牌已过期"),

    /** 旧密码错误 */
    OLD_PASSWORD_ERROR(1009, "旧密码错误"),

    /** 岗位不存在 */
    JOB_POSITION_NOT_EXIST(1010, "岗位不存在"),

    /** 简历记录不存在 */
    RESUME_RECORD_NOT_EXIST(1011, "简历记录不存在"),

    /** 面试记录不存在 */
    INTERVIEW_RECORD_NOT_EXIST(1012, "面试记录不存在"),

    /** 会话记录不存在 */
    SESSION_RECORD_NOT_EXIST(1013, "会话记录不存在"),

    /** AI 服务不可用或调用失败 */
    AI_SERVICE_ERROR(1014, "AI 服务不可用或调用失败"),

    /** PDF 未识别到文本（扫描件等图片型 PDF） */
    RESUME_PDF_TEXT_EMPTY(1015, "未识别到文本，请上传可复制文本的 PDF");

    /** 状态码 */
    private final Integer code;

    /** 提示信息 */
    private final String msg;

    /**
     * 构造方法
     *
     * @param code 状态码
     * @param msg  提示信息
     */
    ResultCode(Integer code, String msg) {
        this.code = code;
        this.msg = msg;
    }
}
