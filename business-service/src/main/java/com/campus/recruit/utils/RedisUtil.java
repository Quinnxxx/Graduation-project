package com.campus.recruit.utils;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.ListOperations;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.SetOperations;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.stereotype.Component;

import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * Redis 常用操作封装
 *
 * <p>基于 {@link RedisTemplate} 封装 String、Hash、List、Set 四类常用操作，统一超时时间单位（秒）。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Component
@RequiredArgsConstructor
public class RedisUtil {

    private final RedisTemplate<String, Object> redisTemplate;

    /* ==================== String 操作 ==================== */

    /**
     * 写入 String 类型缓存（永久有效）
     *
     * @param key   键
     * @param value 值
     */
    public void set(String key, Object value) {
        redisTemplate.opsForValue().set(key, value);
    }

    /**
     * 写入 String 类型缓存（带过期时间）
     *
     * @param key     键
     * @param value   值
     * @param timeout 过期时间（秒）
     */
    public void set(String key, Object value, long timeout) {
        redisTemplate.opsForValue().set(key, value, timeout, TimeUnit.SECONDS);
    }

    /**
     * 仅在键不存在时写入（分布式锁基础操作）
     *
     * @param key   键
     * @param value 值
     * @return 写入成功返回 true
     */
    public boolean setIfAbsent(String key, Object value) {
        return Boolean.TRUE.equals(redisTemplate.opsForValue().setIfAbsent(key, value));
    }

    /**
     * 获取 String 类型缓存
     *
     * @param key 键
     * @return 值，不存在返回 null
     */
    public Object get(String key) {
        return redisTemplate.opsForValue().get(key);
    }

    /**
     * 删除指定键
     *
     * @param key 键
     * @return 删除成功返回 true
     */
    public boolean delete(String key) {
        return Boolean.TRUE.equals(redisTemplate.delete(key));
    }

    /**
     * 批量删除键
     *
     * @param keys 键集合
     * @return 删除数量
     */
    public Long delete(Collection<String> keys) {
        return redisTemplate.delete(keys);
    }

    /**
     * 判断键是否存在
     *
     * @param key 键
     * @return 存在返回 true
     */
    public boolean hasKey(String key) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(key));
    }

    /**
     * 设置过期时间
     *
     * @param key     键
     * @param timeout 过期时间（秒）
     * @return 设置成功返回 true
     */
    public boolean expire(String key, long timeout) {
        return Boolean.TRUE.equals(redisTemplate.expire(key, timeout, TimeUnit.SECONDS));
    }

    /**
     * 获取剩余过期时间
     *
     * @param key 键
     * @return 剩余秒数，键不存在或永久有效返回 -1
     */
    public Long getExpire(String key) {
        return redisTemplate.getExpire(key, TimeUnit.SECONDS);
    }

    /**
     * 自增（用于计数器）
     *
     * @param key 键
     * @return 自增后的值
     */
    public Long increment(String key) {
        return redisTemplate.opsForValue().increment(key);
    }

    /**
     * 自减
     *
     * @param key 键
     * @return 自减后的值
     */
    public Long decrement(String key) {
        return redisTemplate.opsForValue().decrement(key);
    }

    /* ==================== Hash 操作 ==================== */

    /**
     * 写入 Hash 字段
     *
     * @param key   键
     * @param field 字段名
     * @param value 字段值
     */
    public void hSet(String key, String field, Object value) {
        redisTemplate.opsForHash().put(key, field, value);
    }

    /**
     * 批量写入 Hash
     *
     * @param key   键
     * @param values 字段-值映射
     */
    public void hSetAll(String key, Map<String, Object> values) {
        redisTemplate.opsForHash().putAll(key, values);
    }

    /**
     * 获取 Hash 字段值
     *
     * @param key   键
     * @param field 字段名
     * @return 字段值
     */
    public Object hGet(String key, String field) {
        return redisTemplate.opsForHash().get(key, field);
    }

    /**
     * 获取整个 Hash
     *
     * @param key 键
     * @return 字段-值映射
     */
    public Map<Object, Object> hGetAll(String key) {
        return redisTemplate.opsForHash().entries(key);
    }

    /**
     * 删除 Hash 字段
     *
     * @param key    键
     * @param fields 字段名列表
     * @return 删除数量
     */
    public Long hDelete(String key, Object... fields) {
        return redisTemplate.opsForHash().delete(key, fields);
    }

    /**
     * 判断 Hash 字段是否存在
     *
     * @param key   键
     * @param field 字段名
     * @return 存在返回 true
     */
    public boolean hHasKey(String key, String field) {
        return redisTemplate.opsForHash().hasKey(key, field);
    }

    /* ==================== List 操作 ==================== */

    /**
     * 从左侧压入列表
     *
     * @param key   键
     * @param value 值
     * @return 列表长度
     */
    public Long leftPush(String key, Object value) {
        return redisTemplate.opsForList().leftPush(key, value);
    }

    /**
     * 从右侧压入列表
     *
     * @param key   键
     * @param value 值
     * @return 列表长度
     */
    public Long rightPush(String key, Object value) {
        return redisTemplate.opsForList().rightPush(key, value);
    }

    /**
     * 从左侧弹出列表元素
     *
     * @param key 键
     * @return 弹出的值
     */
    public Object leftPop(String key) {
        return redisTemplate.opsForList().leftPop(key);
    }

    /**
     * 从右侧弹出列表元素
     *
     * @param key 键
     * @return 弹出的值
     */
    public Object rightPop(String key) {
        return redisTemplate.opsForList().rightPop(key);
    }

    /**
     * 获取列表指定区间元素
     *
     * @param key   键
     * @param start 起始下标（含）
     * @param end   结束下标（含，-1 表示末尾）
     * @return 元素列表
     */
    public List<Object> range(String key, long start, long end) {
        return redisTemplate.opsForList().range(key, start, end);
    }

    /**
     * 获取列表长度
     *
     * @param key 键
     * @return 列表长度
     */
    public Long listSize(String key) {
        return redisTemplate.opsForList().size(key);
    }

    /* ==================== Set 操作 ==================== */

    /**
     * 向集合添加元素
     *
     * @param key    键
     * @param values 元素列表
     * @return 新增元素数量
     */
    public Long sAdd(String key, Object... values) {
        return redisTemplate.opsForSet().add(key, values);
    }

    /**
     * 获取集合所有元素
     *
     * @param key 键
     * @return 元素集合
     */
    public Set<Object> sMembers(String key) {
        return redisTemplate.opsForSet().members(key);
    }

    /**
     * 从集合移除元素
     *
     * @param key    键
     * @param values 元素列表
     * @return 移除数量
     */
    public Long sRemove(String key, Object... values) {
        return redisTemplate.opsForSet().remove(key, values);
    }

    /**
     * 判断元素是否在集合中
     *
     * @param key   键
     * @param value 元素
     * @return 存在返回 true
     */
    public boolean sIsMember(String key, Object value) {
        return Boolean.TRUE.equals(redisTemplate.opsForSet().isMember(key, value));
    }
}
