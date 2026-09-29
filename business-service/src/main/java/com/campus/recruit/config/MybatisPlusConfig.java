package com.campus.recruit.config;

import com.baomidou.mybatisplus.annotation.DbType;
import com.baomidou.mybatisplus.core.handlers.MetaObjectHandler;
import com.baomidou.mybatisplus.core.incrementer.IdentifierGenerator;
import com.baomidou.mybatisplus.extension.plugins.MybatisPlusInterceptor;
import com.baomidou.mybatisplus.extension.plugins.inner.PaginationInnerInterceptor;
import org.apache.ibatis.reflection.MetaObject;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.LocalDateTime;

/**
 * MyBatis-Plus 配置
 *
 * <p>注册分页插件与公共字段自动填充处理器（createTime / updateTime / isDeleted）。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Configuration
@MapperScan("com.campus.recruit.mapper")
public class MybatisPlusConfig {

    /**
     * 注册容错主键生成器（雪花 ID 时钟回拨兜底）
     *
     * @return 容错标识生成器
     */
    @Bean
    public IdentifierGenerator identifierGenerator() {
        return new TolerantIdentifierGenerator();
    }

    /**
     * 注册 MyBatis-Plus 拦截器（分页插件，MySQL 方言）
     *
     * @return MyBatis-Plus 拦截器
     */
    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();
        interceptor.addInnerInterceptor(new PaginationInnerInterceptor(DbType.MYSQL));
        return interceptor;
    }

    /**
     * 注册公共字段自动填充处理器
     *
     * <p>insert 时自动填充 createTime / updateTime / isDeleted，update 时自动填充 updateTime。</p>
     *
     * @return 元数据自动填充处理器
     */
    @Bean
    public MetaObjectHandler metaObjectHandler() {
        return new MetaObjectHandler() {

            /**
             * 插入时的字段填充策略
             *
             * @param metaObject 元数据对象
             */
            @Override
            public void insertFill(MetaObject metaObject) {
                this.strictInsertFill(metaObject, "createTime", LocalDateTime.class, LocalDateTime.now());
                this.strictInsertFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
                this.strictInsertFill(metaObject, "isDeleted", Integer.class, 0);
            }

            /**
             * 更新时的字段填充策略
             *
             * @param metaObject 元数据对象
             */
            @Override
            public void updateFill(MetaObject metaObject) {
                this.strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
            }
        };
    }
}
