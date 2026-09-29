package com.campus.recruit.config;

import com.baomidou.mybatisplus.core.incrementer.DefaultIdentifierGenerator;
import com.baomidou.mybatisplus.core.incrementer.IdentifierGenerator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.atomic.AtomicLong;

/**
 * 容错主键生成器（MyBatis-Plus 雪花 ID 兜底）。
 *
 * <p>默认委托 {@link DefaultIdentifierGenerator} 生成标准雪花 ID。当容器时钟回拨
 * （WSL2 / Docker 休眠唤醒、NTP 步进校正等场景）触发雪花时钟保护异常
 * （消息含 {@code Clock moved backwards}）时，退化为返回 {@code lastId + 1} 的补偿 ID：
 * 该值严格大于此前任何已发出的 ID，唯一且单调，不依赖时钟，使回拨窗口内的写入不再失败。</p>
 *
 * <p>非时钟回拨异常一律原样抛出，不吞异常，避免掩盖真实数据错误。本类不改变
 * {@code IdType} 语义、不涉及任何表 DDL。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
public class TolerantIdentifierGenerator implements IdentifierGenerator {

    private static final Logger log = LoggerFactory.getLogger(TolerantIdentifierGenerator.class);

    /** 时钟回拨异常的特征消息（MyBatis-Plus {@code Sequence} 抛出的 RuntimeException 字面量）。 */
    private static final String CLOCK_MOVED_BACKWARDS = "Clock moved backwards";

    /** 实际生成器：复用 MyBatis-Plus 单例，避免与默认生成器的 workerId 冲突。 */
    private final IdentifierGenerator delegate;

    /** 已发出的最大 ID，用于时钟回拨时生成严格递增的补偿 ID。 */
    private final AtomicLong lastId = new AtomicLong(0L);

    /**
     * 默认构造：委托 MyBatis-Plus 全局单例雪花生成器。
     */
    public TolerantIdentifierGenerator() {
        this(DefaultIdentifierGenerator.getInstance());
    }

    /**
     * 供验证使用：注入自定义委托生成器。
     *
     * @param delegate 委托生成器
     */
    TolerantIdentifierGenerator(IdentifierGenerator delegate) {
        this.delegate = delegate;
    }

    /**
     * 生成主键：正常委托雪花生成器；捕获时钟回拨异常时返回严格递增的补偿 ID。
     *
     * @param entity 实体对象（透传给委托生成器）
     * @return 主键 ID
     */
    @Override
    public Number nextId(Object entity) {
        try {
            return track(delegate.nextId(entity));
        } catch (RuntimeException e) {
            if (!isClockMovedBackwards(e)) {
                throw e;
            }
            long compensated = lastId.incrementAndGet();
            log.warn("[ID容错] 检测到容器时钟回拨，返回补偿 ID {}（原因：{}）", compensated, e.getMessage());
            return compensated;
        }
    }

    /**
     * 记录已发出的最大 ID。
     *
     * @param id 委托生成器返回的 ID
     * @return 原 ID
     */
    private Number track(Number id) {
        lastId.accumulateAndGet(id.longValue(), Math::max);
        return id;
    }

    /**
     * 判断异常链中是否含时钟回拨特征。
     *
     * @param e 异常
     * @return 含则为 true
     */
    private boolean isClockMovedBackwards(Throwable e) {
        for (Throwable cur = e; cur != null; cur = cur.getCause()) {
            String msg = cur.getMessage();
            if (msg != null && msg.contains(CLOCK_MOVED_BACKWARDS)) {
                return true;
            }
        }
        return false;
    }
}
