package com.nba.predict.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("odds_source")
public class OddsSource {

    @TableId(type = IdType.AUTO)
    private Long sourceId;

    private String sourceName;

    private String sourceCode;

    private String sourceUrl;

    private String sourceType;

    private BigDecimal maeScore;

    private BigDecimal calibrationScore;

    private BigDecimal completenessScore;

    private BigDecimal timelinessScore;

    private BigDecimal stabilityScore;

    private BigDecimal totalScore;

    private Integer priority;

    private Integer isPrimary;

    private String status;

    private LocalDateTime lastCollectTime;

    private String lastError;

    private Integer errorCount;

    private Integer collectInterval;

    private Integer retryCount;

    private Integer timeout;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;
}
