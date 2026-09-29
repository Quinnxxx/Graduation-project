package com.campus.recruit.utils;

import com.campus.recruit.common.ResultCode;
import com.campus.recruit.exception.BusinessException;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import lombok.Getter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * JWT 工具类
 *
 * <p>提供 Token 生成、解析、校验能力。密钥与过期时间通过配置注入，支持环境变量覆盖。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Component
@Getter
public class JwtUtil {

    /** JWT 签名密钥（HS256 要求不小于 32 字节） */
    @Value("${jwt.secret}")
    private String secret;

    /** Token 过期时间（秒） */
    @Value("${jwt.expiration}")
    private Long expiration;

    /** 请求头名称 */
    @Value("${jwt.header}")
    private String header;

    /** Token 前缀 */
    @Value("${jwt.prefix}")
    private String prefix;

    /** 签名密钥对象 */
    private SecretKey secretKey;

    /**
     * 初始化签名密钥
     */
    @PostConstruct
    public void init() {
        this.secretKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    /**
     * 生成 JWT Token
     *
     * @param userId   用户 ID
     * @param username 用户名
     * @return 签名的 JWT 字符串
     */
    public String generateToken(Long userId, String username) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + expiration * 1000);
        return Jwts.builder()
                .setSubject(username)
                .claim("userId", userId)
                .setIssuedAt(now)
                .setExpiration(expiry)
                .signWith(secretKey, SignatureAlgorithm.HS256)
                .compact();
    }

    /**
     * 解析 JWT Token
     *
     * @param token JWT 字符串
     * @return Claims 载荷
     * @throws BusinessException Token 无效或已过期
     */
    public Claims parseToken(String token) {
        try {
            return Jwts.parserBuilder()
                    .setSigningKey(secretKey)
                    .build()
                    .parseClaimsJws(token)
                    .getBody();
        } catch (ExpiredJwtException e) {
            throw new BusinessException(ResultCode.TOKEN_EXPIRED);
        } catch (JwtException | IllegalArgumentException e) {
            throw new BusinessException(ResultCode.TOKEN_INVALID);
        }
    }

    /**
     * 校验 Token 是否有效
     *
     * @param token JWT 字符串
     * @return 有效返回 true
     */
    public boolean validateToken(String token) {
        try {
            parseToken(token);
            return true;
        } catch (BusinessException e) {
            return false;
        }
    }

    /**
     * 从 Token 中获取用户 ID
     *
     * @param token JWT 字符串
     * @return 用户 ID
     */
    public Long getUserId(String token) {
        return parseToken(token).get("userId", Long.class);
    }

    /**
     * 从 Token 中获取用户名
     *
     * @param token JWT 字符串
     * @return 用户名
     */
    public String getUsername(String token) {
        return parseToken(token).getSubject();
    }

    /**
     * 判断 Token 是否已过期
     *
     * @param token JWT 字符串
     * @return 已过期返回 true
     */
    public boolean isTokenExpired(String token) {
        try {
            return parseToken(token).getExpiration().before(new Date());
        } catch (BusinessException e) {
            return true;
        }
    }
}
