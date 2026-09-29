package com.campus.recruit.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.bean.copier.CopyOptions;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.campus.recruit.common.PageResult;
import com.campus.recruit.common.ResultCode;
import com.campus.recruit.dto.ResumeQueryDTO;
import com.campus.recruit.dto.ResumeSaveDTO;
import com.campus.recruit.dto.ResumeUpdateDTO;
import com.campus.recruit.entity.ResumeRecord;
import com.campus.recruit.exception.BusinessException;
import com.campus.recruit.mapper.ResumeRecordMapper;
import com.campus.recruit.service.ResumeRecordService;
import com.campus.recruit.vo.ResumeUploadVO;
import com.campus.recruit.vo.ResumeVO;
import lombok.extern.slf4j.Slf4j;
import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.InvalidPathException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 简历记录服务实现
 *
 * <p>安全约定：按 id 操作（详情/更新/删除）必须先查记录再校验归属，
 * 归属不匹配抛出 {@link ResultCode#FORBIDDEN}，禁止操作他人数据。</p>
 *
 * @author campus-recruit
 * @since 1.0.0
 */
@Slf4j
@Service
public class ResumeRecordServiceImpl extends ServiceImpl<ResumeRecordMapper, ResumeRecord> implements ResumeRecordService {

    /** 简历上传根目录（PDF 上传接口落盘路径，与 docker-compose 卷映射一致） */
    @Value("${resume.upload-dir:/app/uploads/resume}")
    private String uploadDir;

    /** PDF 上传大小上限（5MB） */
    private static final long MAX_FILE_SIZE = 5L * 1024 * 1024;

    /**
     * 上传 PDF 简历：校验格式与大小 → 落盘 → PDFBox 提取文本。
     *
     * <p>校验：非空、后缀 .pdf 且 content-type 为 application/pdf、≤5MB；
     * 提取为空（扫描件等图片型 PDF）返回明确错误。不落库，由前端随创建请求回传文件字段。</p>
     *
     * @param userId 用户 ID
     * @param file   PDF 文件
     * @return 上传结果（fileName / fileSize / filePath / text）
     */
    @Override
    public ResumeUploadVO uploadPdf(Long userId, MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "请选择要上传的 PDF 文件");
        }
        String original = file.getOriginalFilename();
        boolean pdfExt = original != null && original.toLowerCase().endsWith(".pdf");
        if (!pdfExt || !"application/pdf".equalsIgnoreCase(file.getContentType())) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "仅支持上传 PDF 文件");
        }
        if (file.getSize() > MAX_FILE_SIZE) {
            throw new BusinessException(ResultCode.BAD_REQUEST, "PDF 文件不能超过 5MB");
        }
        // 落盘：{uploadDir}/{userId}/{UUID}.pdf（相对路径回传前端，落库前在 create 内二次校验防穿越）
        String relativePath = userId + "/" + UUID.randomUUID() + ".pdf";
        Path root = Paths.get(uploadDir).toAbsolutePath().normalize();
        Path target = root.resolve(relativePath).normalize();
        try {
            Files.createDirectories(target.getParent());
            file.transferTo(target);
        } catch (IOException e) {
            log.error("简历 PDF 保存失败: userId={}, target={}", userId, target, e);
            throw new BusinessException(ResultCode.INTERNAL_ERROR, "简历文件保存失败，请稍后重试");
        }
        // 解析提取文本（扫描件等图片型 PDF 提取为空）
        String text;
        try (PDDocument document = PDDocument.load(target.toFile())) {
            text = new PDFTextStripper().getText(document);
        } catch (IOException e) {
            log.error("简历 PDF 解析失败: userId={}, path={}", userId, relativePath, e);
            throw new BusinessException(ResultCode.BAD_REQUEST, "PDF 解析失败，文件可能已损坏");
        }
        if (!StringUtils.hasText(text)) {
            throw new BusinessException(ResultCode.RESUME_PDF_TEXT_EMPTY);
        }
        ResumeUploadVO vo = new ResumeUploadVO();
        vo.setFileName(original);
        vo.setFileSize(file.getSize());
        vo.setFilePath(relativePath);
        vo.setText(text);
        log.info("简历 PDF 上传成功: userId={}, size={}", userId, file.getSize());
        return vo;
    }

    /**
     * 创建简历记录（初始状态为处理中，待 AI 优化后回填）
     *
     * @param userId 用户 ID
     * @param dto    创建参数
     * @return 简历记录视图对象
     */
    @Override
    public ResumeVO create(Long userId, ResumeSaveDTO dto) {
        ResumeRecord entity = new ResumeRecord();
        BeanUtil.copyProperties(dto, entity);
        entity.setUserId(userId);
        // 防路径穿越：filePath 非空时须位于上传根目录内，非法则忽略文件字段（不报错）
        if (StringUtils.hasText(entity.getFilePath()) && !isSafeFilePath(entity.getFilePath())) {
            entity.setFileName(null);
            entity.setFilePath(null);
            entity.setFileSize(null);
        }
        // 初始状态：0 处理中，AI 优化完成后由 update 回填为 1
        entity.setStatus(0);
        save(entity);
        log.info("创建简历记录成功: userId={}, resumeId={}", userId, entity.getId());
        return toVO(entity);
    }

    /**
     * 校验相对路径解析后位于上传根目录内（防路径穿越）。
     *
     * @param relativePath 存储相对路径（如 {userId}/{UUID}.pdf）
     * @return 合法返回 true
     */
    private boolean isSafeFilePath(String relativePath) {
        try {
            Path root = Paths.get(uploadDir).toAbsolutePath().normalize();
            return root.resolve(relativePath).normalize().startsWith(root);
        } catch (InvalidPathException e) {
            return false;
        }
    }

    /**
     * 分页查询当前用户的简历记录（按创建时间倒序）
     *
     * @param userId 用户 ID
     * @param dto    分页参数
     * @return 分页结果
     */
    @Override
    public PageResult<ResumeVO> pageQuery(Long userId, ResumeQueryDTO dto) {
        Page<ResumeRecord> page = lambdaQuery()
                .eq(ResumeRecord::getUserId, userId)
                .orderByDesc(ResumeRecord::getCreateTime)
                .page(new Page<>(dto.getPageNum(), dto.getPageSize()));
        List<ResumeVO> records = page.getRecords().stream()
                .map(this::toVO)
                .collect(Collectors.toList());
        return PageResult.of(records, page.getTotal(), (long) dto.getPageNum(), (long) dto.getPageSize());
    }

    /**
     * 查询简历记录详情（先查记录，再校验归属）
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     * @return 简历记录视图对象
     */
    @Override
    public ResumeVO getDetail(Long userId, Long id) {
        ResumeRecord entity = getOwnedRecord(userId, id);
        return toVO(entity);
    }

    /**
     * 更新简历记录（AI 优化回填，仅更新非 null 字段，先查记录再校验归属）
     *
     * <p>字段级更新约定：null 表示不修改该字段；空字符串表示清空。</p>
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     * @param dto    更新参数
     * @return 更新后的简历记录视图对象
     */
    @Override
    public ResumeVO update(Long userId, Long id, ResumeUpdateDTO dto) {
        ResumeRecord entity = getOwnedRecord(userId, id);
        // 忽略 null 字段，避免局部更新时清空其他字段
        BeanUtil.copyProperties(dto, entity, CopyOptions.create().setIgnoreNullValue(true));
        updateById(entity);
        log.info("更新简历记录成功: userId={}, resumeId={}", userId, id);
        return toVO(entity);
    }

    /**
     * 删除简历记录（逻辑删除，先查记录再校验归属）
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     */
    @Override
    public void delete(Long userId, Long id) {
        ResumeRecord entity = getOwnedRecord(userId, id);
        removeById(entity.getId());
        log.info("删除简历记录成功: userId={}, resumeId={}", userId, id);
    }

    /**
     * 按 id 查询记录并校验归属当前用户
     *
     * @param userId 用户 ID
     * @param id     记录 ID
     * @return 简历记录实体
     */
    private ResumeRecord getOwnedRecord(Long userId, Long id) {
        ResumeRecord entity = getById(id);
        if (entity == null) {
            throw new BusinessException(ResultCode.RESUME_RECORD_NOT_EXIST);
        }
        // 安全红线：校验记录归属，禁止操作他人数据
        if (!entity.getUserId().equals(userId)) {
            throw new BusinessException(ResultCode.FORBIDDEN, "无权操作他人数据");
        }
        return entity;
    }

    /**
     * 实体转视图对象
     *
     * @param entity 简历记录实体
     * @return 简历记录视图对象
     */
    private ResumeVO toVO(ResumeRecord entity) {
        ResumeVO vo = new ResumeVO();
        BeanUtil.copyProperties(entity, vo);
        return vo;
    }
}
